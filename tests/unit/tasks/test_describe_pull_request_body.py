import unittest

from brigade.tasks.describe_pull_request_body import Correction, PullRequestBodyParts, describe_pull_request_body

CHECK = {
    "head": "c0ffee",
    "checks": [{"command": "python3 -m unittest", "passed": True, "duration_ms": 1240, "tail": []}],
}


class DescribePullRequestBodyTest(unittest.TestCase):
    def test_should_present_the_task_its_criteria_the_verdicts_of_its_check_and_the_attribution(self):
        # Arrange
        no_correction = ()
        parts = PullRequestBodyParts(
            corrections=no_correction,
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

    def test_should_open_on_each_pull_request_corrected_naming_the_task_the_ledger_knows_it_by(self):
        # Arrange
        parts = PullRequestBodyParts(
            corrections=(Correction(pr=7, task="B3"), Correction(pr=9, task=None)),
            title="Empty the cart once",
            specs=("the button empties the cart once",),
            check=CHECK,
            attribution=("Co-Authored-By: Fake Client <fake@example.org>",),
        )

        # Act
        body = describe_pull_request_body(parts)

        # Assert
        self.assertEqual(
            body,
            "Corrects #7 (@TASK.B3)\n"
            "Corrects #9\n"
            "\n"
            "Empty the cart once\n"
            "\n"
            "## Acceptance criteria\n"
            "\n"
            "- the button empties the cart once\n"
            "\n"
            "## Checks of c0ffee\n"
            "\n"
            "- ok `python3 -m unittest` 1.2 s\n"
            "\n"
            "Co-Authored-By: Fake Client <fake@example.org>\n",
        )
