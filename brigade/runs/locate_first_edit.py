from dataclasses import dataclass

from brigade.system.transcripts_answer import TranscriptMessage

USAGE_COUNTERS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


@dataclass(frozen=True)
class FirstEdit:
    steps: int
    tokens: int


def _sum_tokens(messages: tuple[TranscriptMessage, ...]) -> int:
    measured = [message for message in messages if message.usage is not None]
    usage_by_id = {message.id: message.usage for message in measured if message.id is not None}
    usages = [*usage_by_id.values(), *(message.usage for message in measured if message.id is None)]
    return sum(getattr(usage, counter) for usage in usages for counter in USAGE_COUNTERS)


def locate_first_edit(
    messages: tuple[TranscriptMessage, ...], edit_tools: tuple[str, ...], progress_file: str
) -> FirstEdit | None:
    steps = 0
    for position, message in enumerate(messages):
        for tool in message.tools:
            steps += 1
            if tool.name in edit_tools and tool.target != progress_file:
                return FirstEdit(steps=steps, tokens=_sum_tokens(messages[: position + 1]))
    return None
