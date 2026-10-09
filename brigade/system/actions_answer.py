from dataclasses import dataclass

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ClientAction:
    kind: str
    summary: str

    @classmethod
    def from_document(cls, document: dict) -> "ClientAction":
        return cls(kind=document["kind"], summary=document["summary"])

    def to_document(self) -> dict:
        return {"kind": self.kind, "summary": self.summary}


@dataclass(frozen=True)
class ActionsAnswer:
    actions: tuple[ClientAction, ...]

    @classmethod
    def from_document(cls, document: dict) -> "ActionsAnswer":
        return cls(actions=tuple(ClientAction.from_document(action) for action in document["actions"]))

    def to_document(self) -> dict:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, "actions": [action.to_document() for action in self.actions]}
