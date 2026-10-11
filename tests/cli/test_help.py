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
            ("runs", "list the runs and show one"),
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


class BrigadeGroupHelpTest(HelpTestCase):
    def test_should_list_each_action_with_the_help_its_record_declares(self):
        rows = [
            ("adapter", "actions", "answer actions, the request read on stdin"),
            ("adapter", "launch-argv", "answer launch-argv, the request read on stdin"),
            ("adapter", "matrix", "print the capabilities every client adapter declares"),
            ("adapter", "parse-result", "answer parse-result, the request read on stdin"),
            ("adapter", "probe", "answer probe, the request read on stdin"),
            ("adapter", "resume-argv", "answer resume-argv, the request read on stdin"),
            ("adapter", "transcripts", "answer transcripts, the request read on stdin"),
            ("ledger", "budgets", "p50 and p90 steps per procedure over its last runs"),
            ("ledger", "compare", "the runs before a day against the runs from that day on"),
            ("project", "add", "register a git repository in the operational corpus"),
            ("project", "list", "list every registered project"),
            ("project", "pause", "pause a project"),
            ("project", "resume", "resume a paused project"),
            ("project", "show", "print the fields of a project"),
            ("roles", "lint", "check the built-in and the machine role files"),
            ("roles", "list", "list the role, the source and the model of each slot"),
            ("roles", "show", "print the role file a slot resolves to"),
            ("runs", "list", "list every run with its state and outcome"),
            ("runs", "show", "print the summary of a run and its segments, and with --log its journal"),
            ("scheduler", "install", "install the scheduler config.toml names, or the default"),
            ("scheduler", "status", "report the scheduler installed"),
        ]
        for group, action, expected_help in rows:
            with self.subTest(group=group, action=action):
                # Act
                completed = self.run_help(group)

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assert_listed(completed.stdout, action, expected_help)
