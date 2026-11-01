from dataclasses import dataclass
from typing import ClassVar

from brigade.system.reset_hour import ResetHour
from brigade.system.token_usage import TokenUsage

REQUIRED_FIELDS = (
    "run",
    "segment",
    "procedure",
    "slot",
    "role",
    "client",
    "project",
    "session",
    "main_steps",
    "total_steps",
    "duration_ms",
    "outcome",
    "error_class",
    "exit",
    "wave",
    "task",
    "nulls",
)
REQUIRED_BEFORE_USAGE = REQUIRED_FIELDS.index("outcome")
OPTIONAL_FIELDS = (
    "steps_to_first_edit",
    "oversized_output_steps",
    "cost_usd",
    "message",
    "tokens_to_first_edit",
    "role_digest",
    "procedure_digest",
    "shipped_budget",
)


@dataclass(frozen=True)
class RunFinished:
    name: ClassVar[str] = "run.finished"
    run: str
    segment: int
    procedure: str
    slot: str
    role: str
    client: str
    project: str | None
    session: str | None
    main_steps: int | None
    total_steps: int | None
    duration_ms: int | None
    usage: TokenUsage | None
    outcome: str
    error_class: str | None
    exit: int | None
    wave: str | None
    task: str | None
    nulls: dict
    steps_to_first_edit: int | None = None
    oversized_output_steps: int | None = None
    cost_usd: float | None = None
    message: str | None = None
    reset: ResetHour | None = None
    tokens_to_first_edit: int | None = None
    role_digest: str | None = None
    procedure_digest: str | None = None
    shipped_budget: int | None = None

    @classmethod
    def from_document(cls, document: dict) -> "RunFinished":
        usage = document["usage"]
        reset = document.get("reset")
        return cls(
            **{name: document[name] for name in REQUIRED_FIELDS},
            **{name: document.get(name) for name in OPTIONAL_FIELDS},
            usage=None if usage is None else TokenUsage.from_document(usage),
            reset=None if reset is None else ResetHour.from_document(reset),
        )

    def to_document(self) -> dict:
        fields_absent_when_unset = {
            **{name: getattr(self, name) for name in OPTIONAL_FIELDS},
            "reset": None if self.reset is None else self.reset.to_document(),
        }
        return {
            **{name: getattr(self, name) for name in REQUIRED_FIELDS[:REQUIRED_BEFORE_USAGE]},
            "usage": None if self.usage is None else self.usage.to_document(),
            **{name: getattr(self, name) for name in REQUIRED_FIELDS[REQUIRED_BEFORE_USAGE:]},
            **{field: value for field, value in fields_absent_when_unset.items() if value is not None},
        }
