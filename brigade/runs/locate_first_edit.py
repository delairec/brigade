from dataclasses import dataclass
from pathlib import Path

from brigade.system.transcripts_answer import ToolTarget, TranscriptMessage

USAGE_COUNTERS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


@dataclass(frozen=True)
class FirstEdit:
    steps: int
    tokens: int


def sum_tokens(messages: tuple[TranscriptMessage, ...]) -> int:
    measured = [message for message in messages if message.usage is not None]
    usage_by_id = {message.id: message.usage for message in measured if message.id is not None}
    usages = [*usage_by_id.values(), *(message.usage for message in measured if message.id is None)]
    return sum(getattr(usage, counter) for usage in usages for counter in USAGE_COUNTERS)


def _edits_the_worktree(tool: ToolTarget, progress_file: str, worktree: Path) -> bool:
    return tool.target is not None and tool.target != progress_file and Path(tool.target).is_relative_to(worktree)


def locate_first_edit(
    messages: tuple[TranscriptMessage, ...], edit_tools: tuple[str, ...], progress_file: str, worktree: Path
) -> FirstEdit | None:
    steps = 0
    for position, message in enumerate(messages):
        for tool in message.tools:
            steps += 1
            if tool.name in edit_tools and _edits_the_worktree(tool, progress_file, worktree):
                return FirstEdit(steps=steps, tokens=sum_tokens(messages[: position + 1]))
    return None
