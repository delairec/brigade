from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration
from brigade.system.require_configured_client import ConfiguredClient, require_configured_client


def read_configured_client(runtime: Runtime) -> ConfiguredClient:
    path = runtime.paths.configuration_file
    return require_configured_client(read_configuration(path), path)
