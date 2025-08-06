import asyncio
from viam.module.module import Module
try:
    from models.user_defined_metadata import UserDefinedMetadata
except ModuleNotFoundError:
    # when running as local module with run.sh
    from .models.user_defined_metadata import UserDefinedMetadata


if __name__ == '__main__':
    asyncio.run(Module.run_from_registry())
