from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class RunClientSwitched:
    name: ClassVar[str] = "run.client_switched"
    run: str
    client_left: str
    model_left: str | None
    client_taken: str
    model_taken: str | None
    reason: str

    @classmethod
    def from_document(cls, document: dict) -> "RunClientSwitched":
        return cls(
            run=document["run"],
            client_left=document["client_left"],
            model_left=document["model_left"],
            client_taken=document["client_taken"],
            model_taken=document["model_taken"],
            reason=document["reason"],
        )

    def to_document(self) -> dict:
        return {
            "run": self.run,
            "client_left": self.client_left,
            "model_left": self.model_left,
            "client_taken": self.client_taken,
            "model_taken": self.model_taken,
            "reason": self.reason,
        }
