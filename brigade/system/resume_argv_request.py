from dataclasses import dataclass
from typing import ClassVar

from brigade.system.client_role import ClientRole

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ResumeArgvRequest:
    operation: ClassVar[str] = "resume-argv"
    worktree: str
    brief: str
    role: ClientRole
    progress_file: str
    session_id: str
    stop_at: str | None

    @classmethod
    def from_document(cls, document: dict) -> "ResumeArgvRequest":
        return cls(
            worktree=document["worktree"],
            brief=document["brief"],
            role=ClientRole.from_document(document["role"]),
            progress_file=document["progress_file"],
            session_id=document["session_id"],
            stop_at=document["stop_at"],
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "worktree": self.worktree,
            "brief": self.brief,
            "role": self.role.to_document(),
            "progress_file": self.progress_file,
            "session_id": self.session_id,
            "stop_at": self.stop_at,
        }
