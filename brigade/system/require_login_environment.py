from collections.abc import Callable
from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.runtime import Runtime
from brigade.system.ask_login_environment import ask_login_environment

FIRST_DELAY_S = 1.0
DELAY_GROWTH = 2


class LoginUnavailable(BrigadeError):
    pass


@dataclass(frozen=True)
class LoginDemand:
    forge: object
    forge_name: str
    login: str
    key: str
    attempts: int


def require_login_environment(demand: LoginDemand, runtime: Runtime, wait: Callable[[float], None]) -> dict:
    delay_s = FIRST_DELAY_S
    for attempt in range(1, demand.attempts + 1):
        environment = ask_login_environment(demand.forge, demand.forge_name, demand.login, runtime)
        if environment is not None:
            return environment
        if attempt < demand.attempts:
            wait(delay_s)
            delay_s *= DELAY_GROWTH
    append_event(runtime.paths, runtime.now, ForgeAccountUnavailable(login=demand.login, key=demand.key))
    noun = "attempt" if demand.attempts == 1 else "attempts"
    raise LoginUnavailable(
        f"gh printed no token for the login {demand.login}, bound to {demand.key}, after {demand.attempts} {noun}"
    )
