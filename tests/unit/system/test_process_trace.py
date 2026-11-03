import unittest

from brigade.system.process_trace import ProcessTrace
from tests.unit.keep_stderr_as_is import keep_stderr_as_is


class ProcessTraceDocumentTest(unittest.TestCase):
    def test_should_describe_an_exited_process_without_a_pid(self):
        # Arrange
        trace = ProcessTrace(("git", "--version"), "/srv/app", "exited", 0, 3)

        # Act
        document = trace.to_document(keep_stderr_as_is)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "argv": ["git", "--version"],
                "cwd": "/srv/app",
                "exit": 0,
                "duration_ms": 3,
                "outcome": "exited",
            },
        )

    def test_should_describe_a_spawned_run_with_its_pid_and_the_file_that_holds_its_stderr(self):
        # Arrange
        trace = ProcessTrace(
            ("brigade", "run"),
            "/srv/app",
            "spawned",
            None,
            None,
            pid=4242,
            stderr_file="/srv/state/brigade/runs/20261019T090000Z-a1b2c3/brigade.log",
        )

        # Act
        document = trace.to_document(keep_stderr_as_is)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "argv": ["brigade", "run"],
                "cwd": "/srv/app",
                "exit": None,
                "duration_ms": None,
                "outcome": "spawned",
                "pid": 4242,
                "stderr_file": "/srv/state/brigade/runs/20261019T090000Z-a1b2c3/brigade.log",
            },
        )


class ProcessTraceOfAFailedProcessTest(unittest.TestCase):
    def test_should_keep_the_last_two_kibibytes_of_its_masked_stderr(self):
        # Arrange
        lost_head = "warning: the head of a long stderr\n"
        kept_tail = "y" * 2048
        trace = ProcessTrace(("git", "push"), "/srv/app", "exited", 1, 30, stderr=lost_head + kept_tail)

        # Act
        document = trace.to_document(keep_stderr_as_is)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "argv": ["git", "push"],
                "cwd": "/srv/app",
                "exit": 1,
                "duration_ms": 30,
                "outcome": "exited",
                "stderr": "y" * 2048,
            },
        )

    def test_should_drop_the_character_its_cut_splits(self):
        # Arrange
        split_character = "é"
        trace = ProcessTrace(("git", "push"), "/srv/app", "exited", 1, 30, stderr=split_character + "y" * 2047)

        # Act
        document = trace.to_document(keep_stderr_as_is)

        # Assert
        self.assertEqual(document["stderr"], "y" * 2047)

    def test_should_mask_the_whole_stderr_before_keeping_its_tail(self):
        # Arrange
        stderr = "remote: invalid credentials ghp_" + "a" * 2048
        mask = {stderr: "remote: invalid credentials [GitHub token]"}.__getitem__
        trace = ProcessTrace(("git", "push"), "/srv/app", "exited", 1, 30, stderr=stderr)

        # Act
        document = trace.to_document(mask)

        # Assert
        self.assertEqual(document["stderr"], "remote: invalid credentials [GitHub token]")
