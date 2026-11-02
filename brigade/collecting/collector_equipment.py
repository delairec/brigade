from collections.abc import Callable
from dataclasses import dataclass

from brigade.system.parse_configuration import Configuration


@dataclass(frozen=True)
class CollectorEquipment:
    configuration: Configuration
    forge: object
    forge_name: str
    resolve_client: Callable[[str], object]
