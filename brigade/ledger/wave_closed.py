from dataclasses import dataclass
from typing import ClassVar

PR_KEY = "pr"
NO_PULL_REQUEST = None


@dataclass(frozen=True)
class WaveClosed:
    name: ClassVar[str] = "wave.closed"
    wave: str
    pr: int | None = NO_PULL_REQUEST

    @classmethod
    def from_document(cls, document: dict) -> "WaveClosed":
        return cls(wave=document["wave"], pr=document.get(PR_KEY))

    def to_document(self) -> dict:
        recorded_pull_request = {} if self.pr is None else {PR_KEY: self.pr}
        return {"wave": self.wave, **recorded_pull_request}
