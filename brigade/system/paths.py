import os
from dataclasses import dataclass
from pathlib import Path

APPLICATION_DIRECTORY = "brigade"


@dataclass(frozen=True)
class Paths:
    config_root: Path
    state_root: Path
    cache_root: Path
    home: Path
    executable_search_path: str


def _resolve_base(variable: str, home_relative_default: str) -> Path:
    base = Path(os.environ.get(variable, ""))
    if base.is_absolute():
        return base
    return Path.home() / home_relative_default


def build_paths() -> Paths:
    return Paths(
        config_root=_resolve_base("XDG_CONFIG_HOME", ".config") / APPLICATION_DIRECTORY,
        state_root=_resolve_base("XDG_STATE_HOME", ".local/state") / APPLICATION_DIRECTORY,
        cache_root=_resolve_base("XDG_CACHE_HOME", ".cache") / APPLICATION_DIRECTORY,
        home=Path.home(),
        executable_search_path=os.environ.get("PATH", os.defpath),
    )
