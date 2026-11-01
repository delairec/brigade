from dataclasses import dataclass

from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.read_account_environment import ForgeAccount, read_account_environment

FORGE_KIND = "forge"
FORGE_NAME = "github"
BUILD_SLOT = "build"


@dataclass(frozen=True)
class ForgeSlot:
    forge_name: str
    slot: str


def read_forge_environment(configuration: Configuration, forge_slot: ForgeSlot, runtime: Runtime) -> dict:
    account = ForgeAccount(
        forge=runtime.resolve_plugin(FORGE_KIND, forge_slot.forge_name),
        forge_name=forge_slot.forge_name,
        key=forge_slot.slot,
    )
    return read_account_environment(account, configuration, runtime)
