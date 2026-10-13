from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentCreation:
    @classmethod
    def from_document(cls, document: dict) -> "DocumentCreation":
        return cls()
