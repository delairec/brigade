from collections.abc import Callable

from brigade.commands._read_forge_environment import FORGE_KIND
from brigade.tick.forge_login_keeper import ForgeLoginKeeper


def remember_forge_logins(resolve_plugin: Callable[..., object]) -> Callable[..., object]:
    keepers: dict[str, ForgeLoginKeeper] = {}

    def resolve(kind: str, name: str, **options: object) -> object:
        if kind != FORGE_KIND:
            return resolve_plugin(kind, name, **options)
        if name not in keepers:
            keepers[name] = ForgeLoginKeeper(resolve_plugin(kind, name, **options))
        return keepers[name]

    return resolve
