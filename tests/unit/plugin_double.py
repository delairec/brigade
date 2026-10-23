from dataclasses import dataclass


@dataclass(frozen=True)
class PluginDouble:
    kind: str
    name: str
