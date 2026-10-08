from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class ConstraintDelivered:
    name: ClassVar[str] = "constraint.delivered"
    project: str

    @classmethod
    def from_document(cls, document: dict) -> "ConstraintDelivered":
        return cls(project=document["project"])
