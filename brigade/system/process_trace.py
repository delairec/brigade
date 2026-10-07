from dataclasses import dataclass

TRACE_SCHEMA_VERSION = 1
EXITED = "exited"
TIMED_OUT = "timed_out"
NOT_FOUND = "not_found"
CUT = "cut"
SPAWNED = "spawned"


@dataclass(frozen=True)
class ProcessTrace:
    argv: tuple[str, ...]
    cwd: str
    outcome: str
    exit_code: int | None
    duration_ms: int | None
    pid: int | None = None

    def to_document(self) -> dict:
        document = {
            "schema_version": TRACE_SCHEMA_VERSION,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "exit": self.exit_code,
            "duration_ms": self.duration_ms,
            "outcome": self.outcome,
        }
        if self.outcome == SPAWNED:
            return {**document, "pid": self.pid}
        return document
