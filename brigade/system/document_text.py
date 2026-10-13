from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentText:
    text: str

    @classmethod
    def from_document(cls, document: dict) -> "DocumentText":
        return cls(text=document["text"])
