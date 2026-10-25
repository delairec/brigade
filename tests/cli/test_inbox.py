import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.run_while_lock_held import run_while_lock_held
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine


class InboxTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.machine = TemporaryMachine(Path(directory.name).resolve())

    def run_brigade(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, *arguments)


class BrigadeNoteWhileTheInboxIsLockedTest(InboxTestCase):
    def test_should_wait_for_the_lock_of_the_inbox_before_recording(self):
        # Arrange
        lock_file = self.machine.state_home / "brigade" / "locks" / "inbox.lock"
        signals = self.machine.state_home / "brigade" / "inbox" / "signals.jsonl"
        argv = [sys.executable, str(CLONE_ENTRY_POINT), "note", "fix the flaky test"]

        # Act
        with run_while_lock_held(argv, self.machine.describe_environment(), lock_file) as wait_line:
            recorded_while_waiting = signals.exists()

        # Assert
        self.assertEqual(wait_line, f"brigade: waiting for the lock {lock_file}, held by pid 4242\n")
        self.assertFalse(recorded_while_waiting)


class BrigadeInboxDismissTest(InboxTestCase):
    def setUp(self):
        super().setUp()
        self.run_brigade("note", "fix the flaky test")

    def test_should_dismiss_the_signal_its_id_names(self):
        # Act
        completed = self.run_brigade("inbox", "dismiss", "8b0c")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "dismissed 8b0cc9f note:57e52f352e5e\n")
        self.assertEqual(completed.stderr, "")
