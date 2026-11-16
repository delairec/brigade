from dataclasses import dataclass
from typing import ClassVar

from brigade.system.client_role import ClientRole

DOCUMENT_SCHEMA_VERSION = 1


def _read_stop_hook(stop_hook: list[str] | None) -> tuple[str, ...] | None:
    return None if stop_hook is None else tuple(stop_hook)


@dataclass(frozen=True)
class LaunchArgvRequest:
    operation: ClassVar[str] = "launch-argv"
    worktree: str
    brief: str
    role: ClientRole
    progress_file: str
    session_id: str
    stop_at: str | None
    stop_hook: tuple[str, ...] | None

    @classmethod
    def from_document(cls, document: dict) -> "LaunchArgvRequest":
        return cls(
            worktree=document["worktree"],
            brief=document["brief"],
            role=ClientRole.from_document(document["role"]),
            progress_file=document["progress_file"],
            session_id=document["session_id"],
            stop_at=document["stop_at"],
            stop_hook=_read_stop_hook(document["stop_hook"]),
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
            "stop_hook": None if self.stop_hook is None else list(self.stop_hook),
        }
