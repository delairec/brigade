from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PrMerged:
    name: ClassVar[str] = "pr.merged"
    project: str
    wave: str
    task: str
    pr: int
    rounds: int

    @classmethod
    def from_document(cls, document: dict) -> "PrMerged":
        return cls(
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            pr=document["pr"],
            rounds=document["rounds"],
        )
