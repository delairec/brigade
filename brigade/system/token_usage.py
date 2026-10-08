from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int

    @classmethod
    def from_document(cls, document: dict) -> "TokenUsage":
        return cls(
            input_tokens=document["input_tokens"],
            output_tokens=document["output_tokens"],
            cache_creation_input_tokens=document["cache_creation_input_tokens"],
            cache_read_input_tokens=document["cache_read_input_tokens"],
        )

    def to_document(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
        }
