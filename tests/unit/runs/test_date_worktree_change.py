import unittest
from datetime import UTC, datetime

from brigade.runs.date_worktree_change import date_worktree_change
from brigade.runs.locate_first_edit import FirstEdit
from brigade.system.token_usage import TokenUsage
from brigade.system.transcripts_answer import ToolTarget, TranscriptMessage

FIRST_USAGE = TokenUsage(
    input_tokens=1, output_tokens=10, cache_creation_input_tokens=100, cache_read_input_tokens=1000
)
SECOND_USAGE = TokenUsage(
    input_tokens=2, output_tokens=20, cache_creation_input_tokens=200, cache_read_input_tokens=2000
)
THIRD_USAGE = TokenUsage(
    input_tokens=4, output_tokens=40, cache_creation_input_tokens=400, cache_read_input_tokens=4000
)
CHANGED_AT = datetime(2026, 11, 7, 21, 59, 30, tzinfo=UTC)
UNDATED = None


def _create_message(timestamp: str | None, tools: tuple[ToolTarget, ...], usage: TokenUsage) -> TranscriptMessage:
    return TranscriptMessage(
        role="assistant",
        timestamp=timestamp,
        content=[],
        tool_calls=len(tools),
        id=None,
        usage=usage,
        tools=tools,
        calls=(),
        results=(),
    )


class DateWorktreeChangeTest(unittest.TestCase):
    def test_should_date_the_change_at_the_last_tool_call_dated_at_or_before_it(self):
        # Arrange
        messages = (
            _create_message(
                "2026-11-07T21:58:40.000Z", (ToolTarget(name="Read", target="/srv/b46/cli.py"),), FIRST_USAGE
            ),
            _create_message(
                "2026-11-07T21:59:08.000Z",
                (
                    ToolTarget(name="Grep", target="tick"),
                    ToolTarget(name="Bash", target="sed -i 's/hour/minute/' tests/unit/commands/test_tick.py"),
                ),
                SECOND_USAGE,
            ),
            _create_message("2026-11-07T21:59:45.000Z", (ToolTarget(name="Bash", target="git diff"),), THIRD_USAGE),
        )

        # Act
        first_edit = date_worktree_change(messages, CHANGED_AT)

        # Assert
        self.assertEqual(first_edit, FirstEdit(steps=3, tokens=3333))

    def test_should_date_at_its_own_instant_a_call_dated_exactly_at_the_change(self):
        # Arrange
        messages = (
            _create_message("2026-11-07T21:59:30+00:00", (ToolTarget(name="Bash", target="make"),), FIRST_USAGE),
        )

        # Act
        first_edit = date_worktree_change(messages, CHANGED_AT)

        # Assert
        self.assertEqual(first_edit, FirstEdit(steps=1, tokens=1111))

    def test_should_date_no_change_that_no_dated_tool_call_precedes(self):
        # Arrange
        rows = [
            ("no message dated", (_create_message(UNDATED, (ToolTarget(name="Bash", target="make"),), FIRST_USAGE),)),
            (
                "every call dated after the change",
                (_create_message("2026-11-07T22:00:00Z", (ToolTarget(name="Bash", target="make"),), FIRST_USAGE),),
            ),
            ("a dated message with no tool call", (_create_message("2026-11-07T21:58:00Z", (), FIRST_USAGE),)),
        ]
        for case, messages in rows:
            with self.subTest(case=case):
                # Act
                first_edit = date_worktree_change(messages, CHANGED_AT)

                # Assert
                self.assertIsNone(first_edit)
