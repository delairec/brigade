import os
import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa_from import provide_awawa_from
from tests.process_launcher import ProcessLauncher

SCRIPTED_AWAWA_DIRECTORY = Path(__file__).resolve().parent / "fixtures" / "scripted-awawa"
RECORDING_ASKED = "1"


class ProvideAwawaWhileRecordingTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.environment = {
            "PATH": f"{SCRIPTED_AWAWA_DIRECTORY}{os.pathsep}{os.environ['PATH']}",
            "AWAWA_RECORD": RECORDING_ASKED,
        }

    def test_should_have_the_real_awawa_answer_while_the_recordings_are_renewed(self):
        # Arrange
        search_path = provide_awawa_from(self, self.environment, self.root / "recordings")
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        completed = ProcessLauncher.run(
            ["awawa", "fmt", str(self.corpus / "tasks.awawa")],
            cwd=self.root,
            env={**os.environ, "PATH": search_path},
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert
        self.assertEqual(
            [completed.stdout, completed.stderr, completed.returncode],
            [f"{self.corpus}/tasks.awawa\n", "1 file rewritten\n", 0],
        )
