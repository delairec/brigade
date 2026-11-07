import tempfile
import unittest
from pathlib import Path

from brigade.tick.commit_checks import CommandResult, CommitChecks
from brigade.tick.read_commit_checks import read_commit_checks

RECORD = (
    '{"schema_version": 1, "project": "oak", "commit": "c0ffee", "checks": ['
    '{"command": "npm ci", "exit_code": 0}, {"command": "npm test", "exit_code": 1}]}\n'
)


class ReadCommitChecksTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_root = Path(directory.name)

    def test_should_read_each_command_the_tick_ran_on_the_commit_with_its_exit_code(self):
        # Arrange
        record = self.state_root / "commit-checks" / "oak" / "c0ffee.json"
        record.parent.mkdir(parents=True)
        record.write_text(RECORD, encoding="utf-8")

        # Act
        checks = read_commit_checks(self.state_root, "oak", "c0ffee")

        # Assert
        self.assertEqual(
            checks,
            CommitChecks(
                project="oak",
                commit="c0ffee",
                results=(CommandResult(command="npm ci", exit_code=0), CommandResult(command="npm test", exit_code=1)),
            ),
        )

    def test_should_find_no_record_for_a_commit_the_tick_never_checked(self):
        # Act
        checks = read_commit_checks(self.state_root, "oak", "c0ffee")

        # Assert
        self.assertIsNone(checks)
