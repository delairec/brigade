import unittest

from brigade.captures.replace_captures_section import replace_captures_section
from brigade.tasks.describe_pull_request_body import PullRequestBodyParts, describe_pull_request_body

SECTION_AT_0123ABC = (
    "## Captures\n\nEach page at 0123abc.\n\n| Page | Delivered | Reference |\n|---|---|---|\n"
    "| tides | `/c/0123abc/tides-delivered.png` | `/c/0123abc/tides-reference.png` |\n"
    "| ports | `/c/0123abc/ports-delivered.png` | `/c/0123abc/ports-reference.png` |\n"
)
SECTION_AT_4567DEF = (
    "## Captures\n\nEach page at 4567def.\n\n| Page | Delivered | Reference |\n|---|---|---|\n"
    "| tides | `/c/4567def/tides-delivered.png` | `/c/4567def/tides-reference.png` |\n"
)
NO_CAPTURES = ""
NO_CORRECTION = ()


def _compose_body(captures: str) -> str:
    return describe_pull_request_body(
        PullRequestBodyParts(
            corrections=NO_CORRECTION,
            title="Delivers @TASK.T7.",
            specs=("the tides of the week show on one page",),
            check={
                "head": "0123abc",
                "checks": [{"command": "python3 -m unittest", "passed": True, "duration_ms": 1240, "tail": []}],
            },
            attribution=("Co-Authored-By: Fake Client <fake@example.org>", "Claude-Session: https://example.org/s"),
            captures=captures,
        )
    )


class ReplaceCapturesSectionTest(unittest.TestCase):
    def test_should_put_the_captures_of_the_new_head_in_place_of_those_of_the_old_one_keeping_the_attribution(self):
        # Arrange
        body = _compose_body(SECTION_AT_0123ABC)

        # Act
        replaced = replace_captures_section(body, SECTION_AT_4567DEF)

        # Assert
        self.assertEqual(
            replaced,
            "Delivers @TASK.T7.\n\n## Acceptance criteria\n\n- the tides of the week show on one page\n\n"
            "## Checks of 0123abc\n\n- ok `python3 -m unittest` 1.2 s\n\n"
            "## Captures\n\nEach page at 4567def.\n\n| Page | Delivered | Reference |\n|---|---|---|\n"
            "| tides | `/c/4567def/tides-delivered.png` | `/c/4567def/tides-reference.png` |\n\n"
            "Co-Authored-By: Fake Client <fake@example.org>\nClaude-Session: https://example.org/s\n",
        )

    def test_should_put_the_captures_between_the_checks_and_the_attribution_of_a_body_holding_none(self):
        # Arrange
        body = _compose_body(NO_CAPTURES)

        # Act
        replaced = replace_captures_section(body, SECTION_AT_4567DEF)

        # Assert
        self.assertEqual(
            replaced,
            "Delivers @TASK.T7.\n\n## Acceptance criteria\n\n- the tides of the week show on one page\n\n"
            "## Checks of 0123abc\n\n- ok `python3 -m unittest` 1.2 s\n\n"
            "## Captures\n\nEach page at 4567def.\n\n| Page | Delivered | Reference |\n|---|---|---|\n"
            "| tides | `/c/4567def/tides-delivered.png` | `/c/4567def/tides-reference.png` |\n\n"
            "Co-Authored-By: Fake Client <fake@example.org>\nClaude-Session: https://example.org/s\n",
        )

    def test_should_add_the_section_to_a_body_holding_neither_captures_nor_checks(self):
        # Arrange
        body = "The report of @TASK.T7\n"

        # Act
        replaced = replace_captures_section(body, SECTION_AT_4567DEF)

        # Assert
        self.assertEqual(
            replaced,
            "The report of @TASK.T7\n\n## Captures\n\nEach page at 4567def.\n\n"
            "| Page | Delivered | Reference |\n|---|---|---|\n"
            "| tides | `/c/4567def/tides-delivered.png` | `/c/4567def/tides-reference.png` |\n",
        )
