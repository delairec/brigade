import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.runs_prune import COMMAND
from tests.unit.commands.command_runtime import create_runtime
from tests.unit.commands.run_directories import (
    FIRST_RUN,
    SECOND_RUN,
    create_run_record,
    create_run_result,
    write_run,
)

NO_DAY = None
KEEP_FROM_CONFIGURATION = None


class RunsPruneTextTest(unittest.TestCase):
    def test_should_say_that_no_run_was_removed(self):
        # Arrange
        document = {"schema_version": 1, "dry_run": False, "runs": [], "skipped": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no run removed")

    def test_should_name_each_run_removed_or_to_remove(self):
        # Arrange
        rows = [
            ("a pruning", False, f"removed {FIRST_RUN} (finished)"),
            ("a dry run", True, f"would remove {FIRST_RUN} (finished)"),
        ]
        for case, dry_run, expected_text in rows:
            with self.subTest(case=case):
                # Arrange
                document = {
                    "schema_version": 1,
                    "dry_run": dry_run,
                    "runs": [{"run": FIRST_RUN, "state": "finished"}],
                    "skipped": [],
                }

                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, expected_text)


class RunsPruneDiagnosticsTest(unittest.TestCase):
    def test_should_name_each_run_skipped_with_its_reason(self):
        # Arrange
        document = {
            "schema_version": 1,
            "dry_run": False,
            "runs": [],
            "skipped": [{"run": FIRST_RUN, "reason": "run.json is empty"}],
        }

        # Act
        diagnostics = COMMAND.describe_diagnostics(document)

        # Assert
        self.assertEqual(diagnostics, [f"run {FIRST_RUN} skipped, run.json is empty"])


class RunsPruneExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "dry_run": False, "runs": [], "skipped": []})

        # Assert
        self.assertEqual(exit_code, 0)


class RunsPruneRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(keep=1, before=None, resumable=False, dry_run=True)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RunsPruneOfTwoFinishedRunsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        state_root = self.root / "state"
        write_run(
            state_root,
            create_run_record(FIRST_RUN, None, None),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )
        write_run(
            state_root,
            create_run_record(SECOND_RUN, None, None),
            create_run_result(SECOND_RUN, "done", "2026-10-08T09:12:00Z"),
        )

    def test_should_name_the_older_run_beyond_the_bound_asked(self):
        # Arrange
        request = Namespace(keep=1, before=NO_DAY, resumable=False, dry_run=True)

        # Act
        document = COMMAND.run(request, create_runtime(self.root))

        # Assert
        self.assertEqual(
            document,
            {"schema_version": 1, "dry_run": True, "runs": [{"run": FIRST_RUN, "state": "finished"}], "skipped": []},
        )

    def test_should_keep_the_bound_of_the_configuration_when_none_is_asked(self):
        # Arrange
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("runs_kept = 1\n", encoding="utf-8")
        request = Namespace(keep=KEEP_FROM_CONFIGURATION, before=NO_DAY, resumable=False, dry_run=False)

        # Act
        document = COMMAND.run(request, create_runtime(self.root))

        # Assert
        self.assertEqual(
            document,
            {"schema_version": 1, "dry_run": False, "runs": [{"run": FIRST_RUN, "state": "finished"}], "skipped": []},
        )
