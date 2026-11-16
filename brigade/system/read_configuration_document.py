import tomllib
from pathlib import Path

from brigade.errors import BrigadeError


class ConfigurationMissing(BrigadeError):
    pass


def read_configuration_document(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigurationMissing(f"no configuration at {path}; run brigade init") from None
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise BrigadeError(f"{path} is not valid TOML: {error}") from None
