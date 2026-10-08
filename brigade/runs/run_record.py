from dataclasses import dataclass

from brigade.system.validate_document import Field

DOCUMENT_SCHEMA_VERSION = 1
TEXT = Field(kinds=(str,))
RUN_RECORD_SHAPE = {
    "schema_version": Field(kinds=(int,), values=(DOCUMENT_SCHEMA_VERSION,)),
    "run": TEXT,
    "procedure": TEXT,
    "procedure_path": TEXT,
    "slot": TEXT,
    "role": TEXT,
    "role_source": TEXT,
    "client": TEXT,
    "project": Field(kinds=(str,), nullable=True),
    "cwd": TEXT,
    "worktree": TEXT,
    "capabilities": Field(kinds=(list,), items=TEXT),
    "budget": Field(kinds=(int,)),
    "wall_limit_s": Field(kinds=(int, float)),
    "arguments": Field(kinds=(dict,)),
}


@dataclass(frozen=True)
class RunRecord:
    run: str
    procedure: str
    procedure_path: str
    slot: str
    role: str
    role_source: str
    client: str
    project: str | None
    cwd: str
    worktree: str
    capabilities: tuple[str, ...]
    budget: int
    wall_limit_s: float
    arguments: dict

    @classmethod
    def from_document(cls, document: dict) -> "RunRecord":
        return cls(
            run=document["run"],
            procedure=document["procedure"],
            procedure_path=document["procedure_path"],
            slot=document["slot"],
            role=document["role"],
            role_source=document["role_source"],
            client=document["client"],
            project=document["project"],
            cwd=document["cwd"],
            worktree=document["worktree"],
            capabilities=tuple(document["capabilities"]),
            budget=document["budget"],
            wall_limit_s=document["wall_limit_s"],
            arguments=document["arguments"],
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "run": self.run,
            "procedure": self.procedure,
            "procedure_path": self.procedure_path,
            "slot": self.slot,
            "role": self.role,
            "role_source": self.role_source,
            "client": self.client,
            "project": self.project,
            "cwd": self.cwd,
            "worktree": self.worktree,
            "capabilities": list(self.capabilities),
            "budget": self.budget,
            "wall_limit_s": self.wall_limit_s,
            "arguments": self.arguments,
        }
