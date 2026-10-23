from pathlib import Path

from brigade.errors import CannotWrite


def place_directory_atomically(staged: Path, place: Path) -> None:
    if place.is_dir():
        return
    try:
        staged.rename(place)
    except OSError as error:
        raise CannotWrite(place, error) from error
