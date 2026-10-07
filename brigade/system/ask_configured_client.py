from brigade.runtime import Runtime
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_named_client import ask_named_client
from brigade.system.read_configuration import read_configuration

CONFIGURATION_FILE = "config.toml"


def ask_configured_client(client, question: ClientQuestion, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
    return ask_named_client(client, question, configuration, runtime)
