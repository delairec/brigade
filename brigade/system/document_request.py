from dataclasses import dataclass

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DocumentRequest:
    document: str
    path: str
    schema: str
    frame: tuple[str, ...]
    role_has_shell: bool

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "document": self.document,
            "path": self.path,
            "schema": self.schema,
            "frame": list(self.frame),
            "shell": self.role_has_shell,
        }
