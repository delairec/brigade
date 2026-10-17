import time

from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.system.require_login_environment import LoginDemand, require_login_environment

FORGE_NAME = "github"
BUILD_SLOT = "build"
UNBOUND_ENVIRONMENT = {}


def read_forge_environment(configuration: Configuration, slot: str, runtime: Runtime) -> dict:
    login = configuration.forge_accounts.get(slot)
    if login is None:
        return UNBOUND_ENVIRONMENT
    demand = LoginDemand(
        forge=runtime.resolve_plugin("forge", FORGE_NAME),
        forge_name=FORGE_NAME,
        login=login,
        key=slot,
        attempts=configuration.forge_attempts,
    )
    return require_login_environment(demand, runtime, time.sleep)
