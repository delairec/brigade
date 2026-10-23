from pathlib import Path

from brigade.system.parse_configuration import Configuration, parse_configuration

NOTHING_CONFIGURED = Configuration()


def read_optional_configuration(path: Path) -> Configuration:
    if not path.exists():
        return NOTHING_CONFIGURED
    return parse_configuration(path)
