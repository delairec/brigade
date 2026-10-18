from dataclasses import dataclass

from brigade.system.read_configuration import Configuration


@dataclass(frozen=True)
class CollectorEquipment:
    configuration: Configuration
    forge: object
    forge_name: str
