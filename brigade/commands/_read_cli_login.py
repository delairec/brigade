from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.parse_configuration import CLI_KEY, Configuration


def read_cli_login(configuration: Configuration, runtime: Runtime) -> str:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    return ask_forge_account(forge, FORGE_NAME, read_forge_environment(configuration, CLI_KEY, runtime), runtime).login
