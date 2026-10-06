from dataclasses import asdict, dataclass

from brigade.errors import BrigadeError
from brigade.system.ask_client import ClientQuestion, ask_client
from brigade.system.read_configuration import read_configuration
from brigade.system.resolve_plugin import resolve_plugin

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
    completed_request = {
        **request,
        "reasoning_table": {level: asdict(row) for level, row in configuration.reasoning.items()},
        "settings": configuration.clients.get(configuration.client, {}),
        "home": str(runtime.paths.home),
    }
    client = resolve_plugin("client", configuration.client, runtime)
    question = ClientQuestion(client_name=configuration.client, operation=operation, request=completed_request)
    return ConfiguredClientAnswer(client_name=configuration.client, document=ask_client(client, question))
