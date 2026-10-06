from pathlib import Path

from brigade.system.read_configuration import Configuration, read_configuration

NOTHING_CONFIGURED = Configuration()


def read_optional_configuration(path: Path) -> Configuration:
    if not path.exists():
        return NOTHING_CONFIGURED
    return read_configuration(path)
