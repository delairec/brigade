from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentRendering:
    text: str
    entities: list[dict] | None

    @classmethod
    def from_document(cls, document: dict) -> "DocumentRendering":
        return cls(text=document["text"], entities=document["entities"])
