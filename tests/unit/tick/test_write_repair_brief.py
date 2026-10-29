import dataclasses
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.tick.actions import LaunchCheckRepair
from brigade.tick.build_snapshot import PreflightFailure
from brigade.tick.write_repair_brief import write_repair_brief

ACTION = LaunchCheckRepair(
    project="shop",
    wave="shop_w1",
    branch="integration/shop_w1",
    task="B1",
    pr=42,
    worktree="/srv/shop/.brigade/worktrees/B1",
    checks=("tests",),
    findings=(),
)
BRIEF_HEAD = (
    "Repair the failing checks of the pull request #42, which delivers @TASK.B1 of @PROJECT.shop, in the wave shop_w1.\n"
    "\n"
    "- Base branch: integration/shop_w1.\n"
    "- Worktree: /srv/shop/.brigade/worktrees/B1, on the branch task/shop_w1/B1.\n"
    "\n"
    "The tail of the log of each failing check:\n"
    "\n"
    "## tests\n"
    "\n"
)
FAILING_TESTS_LOG = [{"name": "tests", "tail": "FAIL test_cart"}]
PRIVACY_FAILURE = PreflightFailure(
    name="privacy",
    findings=("brigade/cart.py:12: an e-mail address", "README.md:3: a home path"),
)
BODY_FAILURE = PreflightFailure(name="body", findings=("the body keeps the placeholder $summary",))
UNTOUCHED_FILES_FAILURE = PreflightFailure(
    name="untouched", findings=("corpus/tasks.awawa changes while none of its entities does",)
)
COVERAGE_REMEDY = (
    "\n"
    "The coverage check failed: remove each uncovered line, then write it again from a test that demands it,"
    " seen failing first; never write a test after the code it covers.\n"
)


class WriteRepairBriefTest(unittest.TestCase):
    def setUp(self):
        self.state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.state_root)

    def test_should_write_the_tail_of_a_log_free_of_terminal_escape_sequences(self):
        for sequence, tail in [
            ("colour", "\x1b[36;1mpython3 -m unittest\x1b[0m"),
            ("private mode", "\x1b[?25lpython3 -m unittest\x1b[?25h"),
            ("hyperlink ended by a bell", "\x1b]8;;https://example.com\x07python3 -m unittest\x1b]8;;\x07"),
            ("title ended by a string terminator", "\x1b]0;job\x1b\\python3 -m unittest"),
            ("character set", "python3 -m unittest\x1b(B"),
            ("reverse index", "\x1bMpython3 -m unittest"),
        ]:
            with self.subTest(sequence=sequence):
                # Arrange
                logs = [{"name": "tests", "tail": tail}]

                # Act
                path = write_repair_brief(self.state_root, ACTION, logs)

                # Assert
                self.assertEqual(path.read_text(encoding="utf-8"), BRIEF_HEAD + "```\npython3 -m unittest\n```\n")

    def test_should_say_the_log_of_a_check_could_not_be_read(self):
        # Arrange
        logs = [{"name": "tests", "tail": None, "unreadable": True}]

        # Act
        path = write_repair_brief(self.state_root, ACTION, logs)

        # Assert
        self.assertEqual(path.read_text(encoding="utf-8"), BRIEF_HEAD + "The log of this check could not be read.\n")

    def test_should_write_every_other_finding_of_the_preflight_after_the_logs_under_the_name_of_its_check(self):
        # Arrange
        action = dataclasses.replace(ACTION, findings=(PRIVACY_FAILURE, BODY_FAILURE, UNTOUCHED_FILES_FAILURE))

        # Act
        path = write_repair_brief(self.state_root, action, FAILING_TESTS_LOG)

        # Assert
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            BRIEF_HEAD + "```\nFAIL test_cart\n```\n"
            "\n"
            "The other findings of the preflight of the same head:\n"
            "\n"
            "## privacy\n"
            "\n"
            "- brigade/cart.py:12: an e-mail address\n"
            "- README.md:3: a home path\n"
            "\n"
            "## body\n"
            "\n"
            "- the body keeps the placeholder $summary\n"
            "\n"
            "## untouched\n"
            "\n"
            "- corpus/tasks.awawa changes while none of its entities does\n",
        )

    def test_should_name_the_remedy_of_an_uncovered_line_when_the_coverage_check_failed(self):
        for case, checks, expected_ending in [
            ("the coverage check failed", ("tests", "Coverage of the unit tests by coverage.py"), COVERAGE_REMEDY),
            ("the coverage check named in capitals failed", ("tests", "Coverage"), COVERAGE_REMEDY),
            ("the coverage check passed", ("tests",), ""),
        ]:
            with self.subTest(case=case):
                # Arrange
                action = dataclasses.replace(ACTION, checks=checks)

                # Act
                path = write_repair_brief(self.state_root, action, FAILING_TESTS_LOG)

                # Assert
                self.assertEqual(
                    path.read_text(encoding="utf-8"), BRIEF_HEAD + "```\nFAIL test_cart\n```\n" + expected_ending
                )
