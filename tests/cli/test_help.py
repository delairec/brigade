import re
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

TERMINAL_WIDE_ENOUGH_FOR_ONE_LINE_PER_HELP = "200"


class HelpTestCase(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.machine = TemporaryMachine(Path(root.name).resolve())

    def run_help(self, *arguments: str):
        environment = {**self.machine.describe_environment(), "COLUMNS": TERMINAL_WIDE_ENOUGH_FOR_ONE_LINE_PER_HELP}
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments, "--help", environment=environment)

    def assert_listed(self, page: str, name: str, expected_help: str) -> None:
        self.assertRegex(page, rf"\n +{name}\s+{re.escape(expected_help)}\n")


class BrigadeHelpTest(HelpTestCase):
    def test_should_list_each_command_with_the_help_its_record_declares(self):
        # Arrange
        rows = [
            ("adapter", "answer one operation of the configured client adapter, or print the matrix of every adapter"),
            (
                "corpus",
                "read a registered project's tree at a branch, a SHA or a worktree; -- <awawa args> runs awawa there",
            ),
            ("doctor", "check the prerequisites and report the optional items with their fallback"),
            ("init", "create the operational corpus repository, its schema and config.toml"),
            ("ledger", "read the event journal: an overview, a wave or a project"),
            ("project", "register the projects brigade works on, list and show them"),
            ("roles", "list, show and lint the roles each slot resolves to"),
            ("run", "run a procedure as a slot through the client adapter"),
            ("runs", "list the runs, show one, stop one and prune them"),
            ("scheduler", "install what fires the tick, and report it"),
            ("tick", "plan and apply what the facts call for, once or in a loop"),
        ]

        # Act
        completed = self.run_help()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for name, expected_help in rows:
            with self.subTest(command=name):
                self.assert_listed(completed.stdout, name, expected_help)


class BrigadeCorpusHelpTest(HelpTestCase):
    def test_should_print_the_help_of_the_awawa_passthrough_under_its_options(self):
        # Act
        completed = self.run_help("corpus")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout,
            r"\noptions:\n(?:.+\n)+\n"
            + re.escape(
                "-- <awawa args>: run awawa in a registered project's tree"
                " and pass its stdout, stderr and exit code through"
            )
            + r"\n\Z",
        )
