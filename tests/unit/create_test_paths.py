from pathlib import Path

from brigade.system.paths import Paths

PACKAGE_FILE = Path("/srv/brigade/brigade/__init__.py")


def create_test_paths(root: Path) -> Paths:
    return Paths(
        config_root=root / "config" / "brigade",
        state_root=root / "state" / "brigade",
        cache_root=root / "cache" / "brigade",
        home=root,
        executable_search_path="/usr/bin",
        package_file=PACKAGE_FILE,
    )
