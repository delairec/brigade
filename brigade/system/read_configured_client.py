from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration, read_configuration

CONFIGURATION_FILE = "config.toml"


@dataclass(frozen=True)
class ConfiguredClient:
    name: str
    configuration: Configuration


def read_configured_client(runtime: Runtime) -> ConfiguredClient:
    path = runtime.paths.config_root / CONFIGURATION_FILE
    configuration = read_configuration(path)
    if configuration.client is None:
        raise BrigadeError(f"config.toml names no client: set the client key in {path}")
    return ConfiguredClient(name=configuration.client, configuration=configuration)
