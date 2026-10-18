from brigade.runtime import Runtime
from brigade.system.read_account_environment import ForgeAccount, read_account_environment
from brigade.system.read_configuration import Configuration

FORGE_KIND = "forge"
FORGE_NAME = "github"
BUILD_SLOT = "build"


def read_forge_environment(configuration: Configuration, slot: str, runtime: Runtime) -> dict:
    account = ForgeAccount(forge=runtime.resolve_plugin(FORGE_KIND, FORGE_NAME), forge_name=FORGE_NAME, key=slot)
    return read_account_environment(account, configuration, runtime)
