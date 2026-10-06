from pathlib import Path

ROLES_DIRECTORY = "roles"
ROLE_FILE_PATTERN = "*.md"


def list_machine_role_files(config_root: Path) -> tuple[Path, ...]:
    directory = config_root / ROLES_DIRECTORY
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob(ROLE_FILE_PATTERN)))
