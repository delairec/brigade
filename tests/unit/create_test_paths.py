from pathlib import Path

from brigade.system.paths import Paths

PACKAGE_FILE = Path("/srv/brigade/brigade/__init__.py")
NO_SEARCH_PATH = ""


def create_test_paths(
    root: Path, *, run_directory: Path | None = None, executable_search_path: str = NO_SEARCH_PATH
) -> Paths:
    return Paths(
        config_root=root / "config",
        state_root=root / "state",
        cache_root=root / "cache",
        home=root / "home",
        executable_search_path=executable_search_path,
        package_file=PACKAGE_FILE,
        run_directory=run_directory,
    )
