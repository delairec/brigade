from datetime import datetime

from brigade.runs.locate_first_edit import FirstEdit, sum_tokens
from brigade.system.transcripts_answer import TranscriptMessage


def date_worktree_change(messages: tuple[TranscriptMessage, ...], changed_at: datetime) -> FirstEdit | None:
    first_edit = None
    steps = 0
    for position, message in enumerate(messages):
        steps += len(message.tools)
        dated = message.timestamp is not None and datetime.fromisoformat(message.timestamp) <= changed_at
        if dated and message.tools:
            first_edit = FirstEdit(steps=steps, tokens=sum_tokens(messages[: position + 1]))
    return first_edit
