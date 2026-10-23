from pathlib import Path


def list_entry_names(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())
