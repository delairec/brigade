import os
import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa_from import provide_awawa_from
from tests.cli.wave_rehearser import ClassCleanupRegistrar
from tests.process_launcher import ProcessLauncher


class ClassCleanupRegistrarOfACallNeverRecordedTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.recordings = self.root / "recordings"
        self.recordings.mkdir()

    def run_inner_class(self, *arguments: str) -> list:
        directory = self.root
        recordings = self.recordings

        class CallingAwawaTest(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                search_path = provide_awawa_from(ClassCleanupRegistrar(cls), {"PATH": os.environ["PATH"]}, recordings)
                ProcessLauncher.run(
                    ["awawa", *arguments],
                    cwd=directory,
                    env={**os.environ, "PATH": search_path},
                    capture_output=True,
                    text=True,
                    check=False,
                )

            def test_call(self):
                pass

        result = unittest.TestResult()
        unittest.TestSuite([CallingAwawaTest("test_call")]).run(result)
        return result.errors

    def test_should_fail_the_class_of_a_call_never_recorded_saying_how_to_record_it(self):
        # Act
        errors = self.run_inner_class("fmt", "tasks.awawa")

        # Assert
        [(_, error)] = errors
        self.assertIn(
            "awawa has no recording of: awawa fmt tasks.awawa\n"
            "record the calls with awawa on PATH: AWAWA_RECORD=1 python3 -m unittest"
            " tests.cli.test_class_cleanup_registrar.ClassCleanupRegistrarOfACallNeverRecordedTest"
            ".run_inner_class.<locals>.CallingAwawaTest",
            error,
        )
