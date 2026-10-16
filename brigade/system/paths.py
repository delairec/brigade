import os
from dataclasses import dataclass
from pathlib import Path

APPLICATION_DIRECTORY = "brigade"
CONFIGURATION_FILE = "config.toml"
LOCK_DIRECTORY = "locks"
SETUP_DIRECTORY = "setups"
HEARTBEAT_FILE = "tick.json"
SCHEMA_FILE = "_schema.awawa"
RUN_DIRECTORY_VARIABLE = "BRIGADE_RUN_DIR"


@dataclass(frozen=True)
class Paths:
    config_root: Path
    state_root: Path
    cache_root: Path
    home: Path
    executable_search_path: str
    run_directory: Path | None = None

    @property
    def configuration_file(self) -> Path:
        return self.config_root / CONFIGURATION_FILE

    @property
    def lock_directory(self) -> Path:
        return self.state_root / LOCK_DIRECTORY

    @property
    def setup_directory(self) -> Path:
        return self.state_root / SETUP_DIRECTORY

    @property
    def heartbeat_file(self) -> Path:
        return self.state_root / HEARTBEAT_FILE

    @property
    def schema_file(self) -> Path:
        return self.config_root / SCHEMA_FILE


def _resolve_base(variable: str, home_relative_default: str) -> Path:
    base = Path(os.environ.get(variable, ""))
    if base.is_absolute():
        return base
    return Path.home() / home_relative_default


def _resolve_absolute_path(variable: str) -> Path | None:
    path = Path(os.environ.get(variable, ""))
    if path.is_absolute():
        return path
    return None


def build_paths() -> Paths:
    return Paths(
        config_root=_resolve_base("XDG_CONFIG_HOME", ".config") / APPLICATION_DIRECTORY,
        state_root=_resolve_base("XDG_STATE_HOME", ".local/state") / APPLICATION_DIRECTORY,
        cache_root=_resolve_base("XDG_CACHE_HOME", ".cache") / APPLICATION_DIRECTORY,
        home=Path.home(),
        executable_search_path=os.environ.get("PATH", os.defpath),
        run_directory=_resolve_absolute_path(RUN_DIRECTORY_VARIABLE),
    )
