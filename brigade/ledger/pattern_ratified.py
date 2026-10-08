from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PatternRatified:
    name: ClassVar[str] = "pattern.ratified"
    project: str

    @classmethod
    def from_document(cls, document: dict) -> "PatternRatified":
        return cls(project=document["project"])
