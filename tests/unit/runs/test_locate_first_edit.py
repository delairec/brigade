import unittest

from brigade.runs.locate_first_edit import FirstEdit, locate_first_edit
from brigade.system.token_usage import TokenUsage
from brigade.system.transcripts_answer import ToolCall, TranscriptMessage

EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")
PROGRESS_FILE = "/state/brigade/runs/r1/progress.awawa"
NO_TOOLS = ()
NO_USAGE = None
FIRST_USAGE = TokenUsage(
    input_tokens=1, output_tokens=10, cache_creation_input_tokens=100, cache_read_input_tokens=1000
)
SECOND_USAGE = TokenUsage(
    input_tokens=2, output_tokens=20, cache_creation_input_tokens=200, cache_read_input_tokens=2000
)
THIRD_USAGE = TokenUsage(
    input_tokens=4, output_tokens=40, cache_creation_input_tokens=400, cache_read_input_tokens=4000
)


def _create_message(message_id: str | None, tools: tuple[ToolCall, ...], usage: TokenUsage | None) -> TranscriptMessage:
    return TranscriptMessage(
        role="assistant", timestamp=None, content=[], tool_calls=len(tools), id=message_id, usage=usage, tools=tools
    )


class LocateFirstEditTest(unittest.TestCase):
    def test_should_give_the_step_of_the_first_edit_and_the_tokens_of_the_messages_up_to_it(self):
        # Arrange
        messages = (
            TranscriptMessage(
                role="user", timestamp=None, content="Deliver.", tool_calls=0, id=None, usage=NO_USAGE, tools=NO_TOOLS
            ),
            _create_message("msg_1", (ToolCall(name="Read", target="/srv/b42/README.md"),), FIRST_USAGE),
            _create_message(
                "msg_2",
                (ToolCall(name="Bash", target="git status"), ToolCall(name="Edit", target="/srv/b42/brigade/cli.py")),
                SECOND_USAGE,
            ),
            _create_message("msg_3", (ToolCall(name="Edit", target="/srv/b42/brigade/cli.py"),), THIRD_USAGE),
        )

        # Act
        first_edit = locate_first_edit(messages, EDIT_TOOLS, PROGRESS_FILE)

        # Assert
        self.assertEqual(first_edit, FirstEdit(steps=3, tokens=3333))

    def test_should_count_once_the_usage_of_a_message_its_transcript_splits_over_several_lines(self):
        # Arrange
        messages = (
            _create_message("msg_1", (ToolCall(name="Read", target="/srv/b42/README.md"),), FIRST_USAGE),
            _create_message("msg_1", (ToolCall(name="Write", target="/srv/b42/brigade/cli.py"),), FIRST_USAGE),
        )

        # Act
        first_edit = locate_first_edit(messages, EDIT_TOOLS, PROGRESS_FILE)

        # Assert
        self.assertEqual(first_edit, FirstEdit(steps=2, tokens=1111))

    def test_should_pass_over_the_writes_of_the_progress_file(self):
        # Arrange
        messages = (
            _create_message("msg_1", (ToolCall(name="Write", target=PROGRESS_FILE),), FIRST_USAGE),
            _create_message("msg_2", (ToolCall(name="Edit", target="/srv/b42/brigade/cli.py"),), SECOND_USAGE),
        )

        # Act
        first_edit = locate_first_edit(messages, EDIT_TOOLS, PROGRESS_FILE)

        # Assert
        self.assertEqual(first_edit, FirstEdit(steps=2, tokens=3333))

    def test_should_find_no_edit_in_a_session_that_wrote_only_its_progress_or_called_no_edit_tool(self):
        # Arrange
        rows = [
            ("only the progress file", (ToolCall(name="Edit", target=PROGRESS_FILE),)),
            ("no edit tool", (ToolCall(name="Bash", target="python3 -m unittest"), ToolCall(name="Grep", target=None))),
        ]
        for case, tools in rows:
            with self.subTest(case=case):
                # Act
                first_edit = locate_first_edit(
                    (_create_message("msg_1", tools, FIRST_USAGE),), EDIT_TOOLS, PROGRESS_FILE
                )

                # Assert
                self.assertIsNone(first_edit)
