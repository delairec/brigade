from collections.abc import Callable

from brigade.tick.forge_login_keeper import ForgeLoginKeeper

FORGE_KIND = "forge"


def remember_forge_logins(resolve_plugin: Callable[..., object]) -> Callable[..., object]:
    keepers: dict[str, ForgeLoginKeeper] = {}

    def resolve(kind: str, name: str, **options) -> object:
        if kind != FORGE_KIND:
            return resolve_plugin(kind, name, **options)
        if name not in keepers:
            keepers[name] = ForgeLoginKeeper(resolve_plugin(kind, name, **options))
        return keepers[name]

    return resolve
