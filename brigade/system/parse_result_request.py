from dataclasses import dataclass
from typing import ClassVar

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ParseResultRequest:
    operation: ClassVar[str] = "parse-result"
    exit_code: int
    stdout: str
    stderr: str

    @classmethod
    def from_document(cls, document: dict) -> "ParseResultRequest":
        return cls(exit_code=document["exit_code"], stdout=document["stdout"], stderr=document["stderr"])

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }
