from pathlib import PurePosixPath

from brigade.git.count_changed_lines import ChangedFile

NAME = "size"
INFORMATION = "info"
LAYERS = ("domain", "application", "infrastructure", "presentation", "controllers", "composition")


def _count(values: list[str], noun: str) -> str:
    if not values:
        return f"0 {noun}"
    return f"{len(values)} {noun}: {', '.join(values)}"


def measure_size(changed: tuple[ChangedFile, ...]) -> dict:
    paths = [PurePosixPath(file.path) for file in changed]
    packages = sorted({path.parent.as_posix() for path in paths})
    layers = sorted({part for path in paths for part in path.parts[:-1] if part in LAYERS})
    return {
        "name": NAME,
        "verdict": INFORMATION,
        "findings": [
            f"{len(changed)} files",
            f"{sum(file.insertions + file.deletions for file in changed)} lines",
            _count(packages, "packages"),
            _count(layers, "layers"),
        ],
    }
