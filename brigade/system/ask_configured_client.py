from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_named_client import ask_named_client
from brigade.system.read_configuration import read_configuration

CONFIGURATION_FILE = "config.toml"


@dataclass(frozen=True)
class ConfiguredClientAnswer:
    client_name: str
    document: dict


def ask_configured_client(runtime, operation: str, request: dict) -> ConfiguredClientAnswer:
    path = runtime.paths.config_root / CONFIGURATION_FILE
    configuration = read_configuration(path)
    if configuration.client is None:
        raise BrigadeError(f"config.toml names no client: set the client key in {path}")
    question = ClientQuestion(client_name=configuration.client, operation=operation, request=request)
    return ConfiguredClientAnswer(
        client_name=configuration.client, document=ask_named_client(runtime, configuration, question)
    )
