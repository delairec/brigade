from dataclasses import dataclass

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TranscriptMessage:
    role: str
    timestamp: str | None
    content: str | list

    @classmethod
    def from_document(cls, document: dict) -> "TranscriptMessage":
        return cls(role=document["role"], timestamp=document["timestamp"], content=document["content"])

    def to_document(self) -> dict:
        return {"role": self.role, "timestamp": self.timestamp, "content": self.content}


@dataclass(frozen=True)
class TranscriptsAnswer:
    messages: tuple[TranscriptMessage, ...]

    @classmethod
    def from_document(cls, document: dict) -> "TranscriptsAnswer":
        return cls(messages=tuple(TranscriptMessage.from_document(message) for message in document["messages"]))

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "messages": [message.to_document() for message in self.messages],
        }
