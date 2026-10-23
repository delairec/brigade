from brigade.runtime import Runtime
from brigade.system.parse_configuration import parse_configuration
from brigade.system.require_configured_client import ConfiguredClient, require_configured_client


def read_configured_client(runtime: Runtime) -> ConfiguredClient:
    path = runtime.paths.configuration_file
    return require_configured_client(parse_configuration(path), path)
