import unittest

from brigade.system.process_trace import ProcessTrace


class ProcessTraceDocumentTest(unittest.TestCase):
    def test_should_describe_an_exited_process_without_a_pid(self):
        # Arrange
        trace = ProcessTrace(("git", "--version"), "/srv/app", "exited", 0, 3)

        # Act
        document = trace.to_document()

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

    def test_should_describe_a_spawned_run_with_its_pid(self):
        # Arrange
        trace = ProcessTrace(("brigade", "run"), "/srv/app", "spawned", None, None, pid=4242)

        # Act
        document = trace.to_document()

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
            },
        )
