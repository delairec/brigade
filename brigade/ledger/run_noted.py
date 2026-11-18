from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class RunNoted:
    name: ClassVar[str] = "run.noted"
    run: str
    text: str

    @classmethod
    def from_document(cls, document: dict) -> "RunNoted":
        return cls(run=document["run"], text=document["text"])

    def to_document(self) -> dict:
        return {"run": self.run, "text": self.text}
