from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.read_configuration import read_configuration

CONFIGURATION_FILE = "config.toml"


def read_configured_client_name(runtime: Runtime) -> str:
    path = runtime.paths.config_root / CONFIGURATION_FILE
    client = read_configuration(path).client
    if client is None:
        raise BrigadeError(f"config.toml names no client: set the client key in {path}")
    return client
