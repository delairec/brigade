import time
from dataclasses import dataclass

from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.system.require_login_environment import LoginDemand, require_login_environment

UNBOUND_ENVIRONMENT = {}


@dataclass(frozen=True)
class ForgeAccount:
    forge: object
    forge_name: str
    key: str


def read_account_environment(account: ForgeAccount, configuration: Configuration, runtime: Runtime) -> dict:
    login = configuration.forge_accounts.get(account.key)
    if login is None:
        return UNBOUND_ENVIRONMENT
    demand = LoginDemand(
        forge=account.forge,
        forge_name=account.forge_name,
        login=login,
        key=account.key,
        attempts=configuration.forge_attempts,
    )
    return require_login_environment(demand, runtime, time.sleep)
