from dataclasses import dataclass

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class AccountRequest:
    environment: dict

    def to_document(self) -> dict:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, "environment": self.environment}
