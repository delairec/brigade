from dataclasses import dataclass


@dataclass(frozen=True)
class UndeclaredEvent:
    name: str

    @classmethod
    def from_document(cls, document: dict) -> "UndeclaredEvent":
        return cls(name=document["event"])
