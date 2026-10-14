from dataclasses import dataclass


@dataclass(frozen=True)
class EntryDetection:
    holds_entry: bool

    @classmethod
    def from_document(cls, document: dict) -> "EntryDetection":
        return cls(holds_entry=document["holds_entry"])
