from dataclasses import dataclass

from brigade.corpus.quote_awawa_string import quote_awawa_string

PLANNING_STATUS = "planning"


@dataclass(frozen=True)
class NewRequest:
    project: str
    text: str
    pattern: str | None = None


def render_request_block(name: str, new_request: NewRequest, created_at: str) -> str:
    block = (
        f"REQUEST {name}\n"
        f"\tPROJECT @PROJECT.{new_request.project}\n"
        f"\tTEXT {quote_awawa_string(new_request.text)}\n"
        f"\tCREATED_AT {quote_awawa_string(created_at)}\n"
        f"\tSTATUS {PLANNING_STATUS}\n"
    )
    if new_request.pattern is None:
        return block
    return block + f"\tFROM @PATTERN.{new_request.pattern}\n"
