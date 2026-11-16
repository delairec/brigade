import tomllib
from importlib.resources.abc import Traversable

from brigade.errors import BrigadeError
from brigade.preflights.run_preflight import PREFLIGHT_SHAPE, PREFLIGHT_SUFFIX
from brigade.system.validate_document import validate_document


def read_preflight_file(directory: Traversable, name: str) -> dict | None:
    file = directory / f"{name}{PREFLIGHT_SUFFIX}"
    if not file.is_file():
        return None
    try:
        document = tomllib.loads(file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BrigadeError(f"the preflight file {file} is no TOML document: {error}") from None
    validate_document(document, PREFLIGHT_SHAPE)
    return document
