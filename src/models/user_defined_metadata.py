import os
from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)

from typing_extensions import Self
from viam.components.sensor import *
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import Geometry, ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading, ValueTypes
from viam.app.viam_client import ViamClient
from viam.rpc.dial import DialOptions, Credentials


class UserDefinedMetadata(Sensor, EasyResource):
    # To enable debug-level logging, either run viam-server with the --debug option,
    # or configure your resource/machine to display debug logs.
    MODEL: ClassVar[Model] = Model(
        ModelFamily("mcvella", "sensor"), "user-defined-metadata"
    )

    def __init__(self, name: str):
        super().__init__(name)
        self._viam_client = None

    async def _get_viam_client(self) -> ViamClient:
        """Get or create a ViamClient instance."""
        if self._viam_client is None:
            # Get credentials from environment variables
            api_key = os.getenv("VIAM_API_KEY")
            api_key_id = os.getenv("VIAM_API_KEY_ID")
            
            if not api_key or not api_key_id:
                raise ValueError("VIAM_API_KEY and VIAM_API_KEY_ID environment variables must be set")
            
            dial_options = DialOptions.with_api_key( 
                api_key=api_key,
                api_key_id=api_key_id
            )
            
            self._viam_client = await ViamClient.create_from_dial_options(dial_options)
            
        return self._viam_client

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Sensor component.
        The default implementation sets the name from the `config` parameter and then calls `reconfigure`.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both required and optional)

        Returns:
            Self: The resource
        """
        return super().new(config, dependencies)

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any required dependencies or optional dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Tuple[Sequence[str], Sequence[str]]: A tuple where the
                first element is a list of required dependencies and the
                second element is a list of optional dependencies
        """
        return [], []

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """This method allows you to dynamically update your service when it receives a new `config` object.

        Args:
            config (ComponentConfig): The new configuration
            dependencies (Mapping[ResourceName, ResourceBase]): Any dependencies (both required and optional)
        """
        return super().reconfigure(config, dependencies)

    async def get_readings(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, SensorReading]:
        """Get robot and robot part user-defined metadata.
        
        Returns:
            Mapping[str, SensorReading]: Dictionary with 'robot' and 'part' keys containing 
                                       the respective metadata
        """
        try:
            # Get required environment variables
            robot_id = os.getenv("VIAM_MACHINE_ID")
            robot_part_id = os.getenv("VIAM_MACHINE_PART_ID")
            
            if not robot_id:
                raise ValueError("VIAM_MACHINE_ID environment variable is required")
            if not robot_part_id:
                raise ValueError("VIAM_MACHINE_PART_ID environment variable is required")
            
            # Get viam client
            viam_client = await self._get_viam_client()
            app_client = viam_client.app_client
            # Fetch robot and robot part metadata
            robot_metadata = await app_client.get_robot_metadata(robot_id)
            part_metadata = await app_client.get_robot_part_metadata(robot_part_id)
            
            return {
                "robot": robot_metadata,
                "part": part_metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching metadata: {e}")
            # Return empty metadata in case of error
            return {
                "robot": {},
                "part": {}
            }

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        """Handle update commands for user-defined metadata.
        
        Expected command format:
        {
            "command": "update",
            "scope": "part|robot", 
            "metadata": <python dict>
        }
        
        Args:
            command: Dictionary containing the command parameters
            timeout: Optional timeout for the operation
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate command structure
            if not isinstance(command, dict):
                raise ValueError("Command must be a dictionary")
                
            cmd = command.get("command")
            scope = command.get("scope")
            metadata = command.get("metadata")
            
            if cmd != "update":
                raise ValueError(f"Unsupported command: {cmd}. Only 'update' is supported.")
                
            if scope not in ["part", "robot"]:
                raise ValueError(f"Invalid scope: {scope}. Must be 'part' or 'robot'.")
                
            if not isinstance(metadata, dict):
                raise ValueError("metadata must be a dictionary")
            
            # Get required environment variables
            robot_id = os.getenv("VIAM_MACHINE_ID")
            robot_part_id = os.getenv("VIAM_MACHINE_PART_ID")
            
            if not robot_id:
                raise ValueError("VIAM_MACHINE_ID environment variable is required")
            if not robot_part_id:
                raise ValueError("VIAM_MACHINE_PART_ID environment variable is required")
            
            # Get viam client
            viam_client = await self._get_viam_client()
            app_client = viam_client.app_client

            # Update metadata based on scope
            if scope == "robot":
                await app_client.update_robot_metadata(robot_id, metadata)
                self.logger.info(f"Successfully updated robot metadata for robot {robot_id}")
                return {
                    "success": True,
                    "message": f"Robot metadata updated successfully",
                    "scope": "robot",
                    "robot_id": robot_id
                }
            elif scope == "part":
                await app_client.update_robot_part_metadata(robot_part_id, metadata)
                self.logger.info(f"Successfully updated robot part metadata for part {robot_part_id}")
                return {
                    "success": True,
                    "message": f"Robot part metadata updated successfully",
                    "scope": "part",
                    "robot_part_id": robot_part_id
                }
                
        except Exception as e:
            error_msg = f"Error updating metadata: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "scope": command.get("scope", "unknown"),
                "command": command.get("command", "unknown")
            }

    async def get_geometries(
        self, *, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> List[Geometry]:
        self.logger.error("`get_geometries` is not implemented")
        raise NotImplementedError()

