from dataclasses import dataclass

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ClientCommand:
    argv: tuple[str, ...]
    environment: dict
    stdin: str | None
    session_id: str | None

    @classmethod
    def from_document(cls, document: dict) -> "ClientCommand":
        return cls(
            argv=tuple(document["argv"]),
            environment=document["environment"],
            stdin=document["stdin"],
            session_id=document["session_id"],
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "argv": list(self.argv),
            "environment": self.environment,
            "stdin": self.stdin,
            "session_id": self.session_id,
        }
