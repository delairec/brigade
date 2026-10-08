from dataclasses import dataclass
from typing import ClassVar

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TranscriptsRequest:
    operation: ClassVar[str] = "transcripts"
    session_id: str
    worktree: str

    @classmethod
    def from_document(cls, document: dict) -> "TranscriptsRequest":
        return cls(session_id=document["session_id"], worktree=document["worktree"])

    def to_document(self) -> dict:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, "session_id": self.session_id, "worktree": self.worktree}
