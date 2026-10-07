import tempfile
import unittest
from pathlib import Path

from brigade.errors import ToolNotFound
from brigade.system.spawn_process import SpawnRequest, spawn_process

PROCESS_WAIT_S = 10.0
LARGER_THAN_A_PIPE = "x" * 1_048_576
STILL_RUNNING = None


class SpawnProcessTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.stdout = Path(self.root.name) / "stdout.log"
        self.stderr = Path(self.root.name) / "stderr.log"

    def spawn(self, argv: tuple, stdin):
        process = spawn_process(
            SpawnRequest(
                argv=argv, cwd=self.root.name, environment={}, stdin=stdin, stdout=self.stdout, stderr=self.stderr
            )
        )
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process


class SpawnProcessWithABriefTest(SpawnProcessTestCase):
    def test_should_hand_the_brief_to_the_process_on_its_standard_input(self):
        # Arrange
        process = self.spawn(("cat",), "Deliver the task B70.\n")

        # Act
        process.wait(timeout=PROCESS_WAIT_S)

        # Assert
        self.assertEqual(self.stdout.read_text(), "Deliver the task B70.\n")

    def test_should_hand_the_process_over_before_it_reads_its_brief(self):
        # Act
        process = self.spawn(("sleep", "30"), LARGER_THAN_A_PIPE)

        # Assert
        self.assertEqual(process.poll(), STILL_RUNNING)

    def test_should_hand_a_brief_larger_than_a_pipe_whole(self):
        # Arrange
        process = self.spawn(("cat",), LARGER_THAN_A_PIPE)

        # Act
        process.wait(timeout=PROCESS_WAIT_S)

        # Assert
        self.assertEqual(self.stdout.read_text(), LARGER_THAN_A_PIPE)


class SpawnProcessOfAMissingToolTest(SpawnProcessTestCase):
    def test_should_refuse_naming_the_tool_not_on_path(self):
        # Act
        with self.assertRaises(ToolNotFound) as refusal:
            spawn_process(
                SpawnRequest(
                    argv=("brigade-no-such-tool",),
                    cwd=self.root.name,
                    environment={},
                    stdin=None,
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
            )

        # Assert
        self.assertEqual(str(refusal.exception), "brigade-no-such-tool not on PATH")
