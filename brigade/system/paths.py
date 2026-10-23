import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import brigade

APPLICATION_DIRECTORY = "brigade"
CONFIGURATION_FILE = "config.toml"
LOCK_DIRECTORY = "locks"
SETUP_DIRECTORY = "setups"
HEARTBEAT_FILE = "tick.json"
SCHEMA_FILE = "_schema.awawa"
RUN_DIRECTORY_VARIABLE = "BRIGADE_RUN_DIR"
HOME_VARIABLE = "HOME"


@dataclass(frozen=True)
class Paths:
    config_root: Path
    state_root: Path
    cache_root: Path
    home: Path
    executable_search_path: str
    package_file: Path
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


def _resolve_base(environment: Mapping[str, str], variable: str, home: Path, home_relative_default: str) -> Path:
    base = Path(environment.get(variable, ""))
    if base.is_absolute():
        return base
    return home / home_relative_default


def _resolve_absolute_path(environment: Mapping[str, str], variable: str) -> Path | None:
    path = Path(environment.get(variable, ""))
    if path.is_absolute():
        return path
    return None


def _resolve_home(environment: Mapping[str, str]) -> Path:
    if HOME_VARIABLE in environment:
        return Path(environment[HOME_VARIABLE])
    return Path.home()


def build_paths(environment: Mapping[str, str]) -> Paths:
    home = _resolve_home(environment)
    return Paths(
        config_root=_resolve_base(environment, "XDG_CONFIG_HOME", home, ".config") / APPLICATION_DIRECTORY,
        state_root=_resolve_base(environment, "XDG_STATE_HOME", home, ".local/state") / APPLICATION_DIRECTORY,
        cache_root=_resolve_base(environment, "XDG_CACHE_HOME", home, ".cache") / APPLICATION_DIRECTORY,
        home=home,
        executable_search_path=environment.get("PATH", os.defpath),
        package_file=Path(brigade.__file__),
        run_directory=_resolve_absolute_path(environment, RUN_DIRECTORY_VARIABLE),
    )
