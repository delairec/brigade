import unittest

from brigade.tasks.describe_pull_request_body import PullRequestBodyParts, describe_pull_request_body


class DescribePullRequestBodyTest(unittest.TestCase):
    def test_should_present_the_task_its_criteria_the_verdicts_of_its_check_and_the_attribution(self):
        # Arrange
        parts = PullRequestBodyParts(
            title="Empty the cart in one click",
            specs=("the button empties the cart", "the emptying charges nothing"),
            check={
                "head": "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
                "checks": [
                    {"command": "python3 -m unittest", "passed": True, "duration_ms": 1240, "tail": []},
                    {"command": "awawa lint --strict .", "passed": True, "duration_ms": 80, "tail": []},
                ],
            },
            attribution=("Co-Authored-By: Fake Client <fake@example.org>",),
            captures="",
        )

        # Act
        body = describe_pull_request_body(parts)

        # Assert
        self.assertEqual(
            body,
            "Empty the cart in one click\n"
            "\n"
            "## Acceptance criteria\n"
            "\n"
            "- the button empties the cart\n"
            "- the emptying charges nothing\n"
            "\n"
            "## Checks of 4b825dc642cb6eb9a060e54bf8d69288fbee4904\n"
            "\n"
            "- ok `python3 -m unittest` 1.2 s\n"
            "- ok `awawa lint --strict .` 0.1 s\n"
            "\n"
            "Co-Authored-By: Fake Client <fake@example.org>\n",
        )


class DescribePullRequestBodyWithCapturesTest(unittest.TestCase):
    def test_should_show_the_captures_after_the_checks(self):
        # Arrange
        parts = PullRequestBodyParts(
            title="Empty the cart in one click",
            specs=("the button empties the cart",),
            check={
                "head": "4b825dc",
                "checks": [{"command": "python3 -m unittest", "passed": True, "duration_ms": 1240, "tail": []}],
            },
            attribution=("Co-Authored-By: Fake Client <fake@example.org>",),
            captures="## Captures\n\n| cart | ![cart delivered](d.png) | ![cart reference](r.png) |\n",
        )

        # Act
        body = describe_pull_request_body(parts)

        # Assert
        self.assertEqual(
            body,
            "Empty the cart in one click\n"
            "\n"
            "## Acceptance criteria\n"
            "\n"
            "- the button empties the cart\n"
            "\n"
            "## Checks of 4b825dc\n"
            "\n"
            "- ok `python3 -m unittest` 1.2 s\n"
            "\n"
            "## Captures\n"
            "\n"
            "| cart | ![cart delivered](d.png) | ![cart reference](r.png) |\n"
            "\n"
            "Co-Authored-By: Fake Client <fake@example.org>\n",
        )
