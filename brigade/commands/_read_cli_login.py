from brigade.commands._read_forge_environment import ForgeSlot, read_forge_environment
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.parse_configuration import CLI_KEY, Configuration


def read_cli_login(configuration: Configuration, forge_name: str, runtime: Runtime) -> str:
    forge = runtime.resolve_plugin("forge", forge_name)
    return ask_forge_account(
        forge, forge_name, read_forge_environment(configuration, ForgeSlot(forge_name, CLI_KEY), runtime), runtime
    ).login
