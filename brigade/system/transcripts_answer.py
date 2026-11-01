from dataclasses import dataclass

from brigade.system.token_usage import TokenUsage

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ToolCall:
    name: str
    target: str | None


@dataclass(frozen=True)
class TranscriptMessage:
    role: str
    timestamp: str | None
    content: str | list
    tool_calls: int
    id: str | None
    usage: TokenUsage | None
    tools: tuple[ToolCall, ...]

    @classmethod
    def from_document(cls, document: dict) -> "TranscriptMessage":
        usage = document["usage"]
        return cls(
            role=document["role"],
            timestamp=document["timestamp"],
            content=document["content"],
            tool_calls=document["tool_calls"],
            id=document["id"],
            usage=None if usage is None else TokenUsage.from_document(usage),
            tools=tuple(ToolCall(name=tool["name"], target=tool["target"]) for tool in document["tools"]),
        )

    def to_document(self) -> dict:
        return {
            "role": self.role,
            "timestamp": self.timestamp,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tools": [{"name": tool.name, "target": tool.target} for tool in self.tools],
            "id": self.id,
            "usage": None if self.usage is None else self.usage.to_document(),
        }


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
