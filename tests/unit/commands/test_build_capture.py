import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.build_capture import COMMAND
from tests.unit.commands.command_runtime import create_machine_double
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

TASK_WORKTREE = {
    ("git", "rev-parse", "--show-toplevel"): "/srv/tidepool-T7\n",
    ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): "/srv/tidepool/.git\n",
    ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"): "8885daa\n",
}
TIDEPOOL = {"PROJECT": {"tidepool": (("PATH", "/srv/tidepool"), ("MAIN", "main"))}, "TASK": {"T7": ()}}
DEFAULT_DIRECTORY = None


class BuildCaptureTextTest(unittest.TestCase):
    def test_should_print_each_page_with_its_two_captures_then_why_a_reference_is_not_captured(self):
        # Arrange
        document = {
            "pages": [{"page": "home", "delivered": "/c/home-delivered.png", "reference": "/c/home-reference.png"}],
            "skipped": ["https://example.org/harbour: a REFERENCE is a repository path, a URL is not captured"],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "home: /c/home-delivered.png | /c/home-reference.png\n"
            "https://example.org/harbour: a REFERENCE is a repository path, a URL is not captured",
        )


class BuildCaptureTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.paths = create_test_paths(self.root)
        self.runtime = create_test_runtime(self.paths, run_process=create_machine_double(TIDEPOOL, TASK_WORKTREE))

    def test_should_say_plainly_that_a_task_citing_no_reference_has_no_capture(self):
        # Act
        document = COMMAND.run(Namespace(task="T7", directory=DEFAULT_DIRECTORY), self.runtime)

        # Assert
        self.assertEqual(document["skipped"], ["the task carries no REFERENCE: no capture"])

    def test_should_write_the_captures_of_the_head_under_the_state_directory_unless_told_where(self):
        # Arrange
        rows = [
            ("by default", DEFAULT_DIRECTORY, str(self.paths.state_root / "captures" / "tidepool" / "T7" / "8885daa")),
            ("told where", str(self.root / "elsewhere"), str(self.root / "elsewhere")),
        ]
        for case, directory, expected_directory in rows:
            with self.subTest(case=case):
                # Act
                document = COMMAND.run(Namespace(task="T7", directory=directory), self.runtime)

                # Assert
                self.assertEqual(document["directory"], expected_directory)
