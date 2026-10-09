from dataclasses import dataclass

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TranscriptMessage:
    role: str
    timestamp: str | None
    content: str | list
    tool_calls: int

    @classmethod
    def from_document(cls, document: dict) -> "TranscriptMessage":
        return cls(
            role=document["role"],
            timestamp=document["timestamp"],
            content=document["content"],
            tool_calls=document["tool_calls"],
        )

    def to_document(self) -> dict:
        return {"role": self.role, "timestamp": self.timestamp, "content": self.content, "tool_calls": self.tool_calls}


def _read_messages(documents: list) -> tuple[TranscriptMessage, ...]:
    return tuple(TranscriptMessage.from_document(document) for document in documents)


@dataclass(frozen=True)
class SubAgentTranscript:
    messages: tuple[TranscriptMessage, ...]

    @classmethod
    def from_document(cls, document: dict) -> "SubAgentTranscript":
        return cls(messages=_read_messages(document["messages"]))

    def to_document(self) -> dict:
        return {"messages": [message.to_document() for message in self.messages]}


@dataclass(frozen=True)
class TranscriptsAnswer:
    messages: tuple[TranscriptMessage, ...]
    subagents: tuple[SubAgentTranscript, ...]

    @classmethod
    def from_document(cls, document: dict) -> "TranscriptsAnswer":
        return cls(
            messages=_read_messages(document["messages"]),
            subagents=tuple(SubAgentTranscript.from_document(subagent) for subagent in document["subagents"]),
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "messages": [message.to_document() for message in self.messages],
            "subagents": [subagent.to_document() for subagent in self.subagents],
        }
