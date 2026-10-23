from dataclasses import dataclass
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration


@dataclass(frozen=True)
class ConfiguredClient:
    name: str
    configuration: Configuration


def require_configured_client(configuration: Configuration, path: Path) -> ConfiguredClient:
    if configuration.client is None:
        raise BrigadeError(f"config.toml names no client: set the client key in {path}")
    return ConfiguredClient(name=configuration.client, configuration=configuration)
