from dataclasses import dataclass

from brigade.system.validate_document import Field

DOCUMENT_SCHEMA_VERSION = 1
NO_ACTION_FAILED = 0
HEARTBEAT_SHAPE = {
    "schema_version": Field(kinds=(int,), values=(DOCUMENT_SCHEMA_VERSION,)),
    "ts": Field(kinds=(str,)),
    "duration_ms": Field(kinds=(int,)),
    "actions_applied": Field(kinds=(int,)),
    "actions_failed": Field(kinds=(int,), optional=True),
}


@dataclass(frozen=True)
class Heartbeat:
    ts: str
    duration_ms: int
    actions_applied: int
    actions_failed: int

    @classmethod
    def from_document(cls, document: dict) -> "Heartbeat":
        return cls(
            ts=document["ts"],
            duration_ms=document["duration_ms"],
            actions_applied=document["actions_applied"],
            actions_failed=document.get("actions_failed", NO_ACTION_FAILED),
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "ts": self.ts,
            "duration_ms": self.duration_ms,
            "actions_applied": self.actions_applied,
            "actions_failed": self.actions_failed,
        }
