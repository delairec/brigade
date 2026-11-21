import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.build_capture import COMMAND
from tests.unit.captures.take_screenshots_or import take_screenshots_or
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


class BuildCaptureOfATaskCitingAReferenceTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.paths = create_test_paths(self.root)
        self.worktree = self.root / "tidepool-T7"
        (self.worktree / "artifact").mkdir(parents=True)
        (self.worktree / "artifact" / "harbour.html").write_text('<html><head></head><section id="tides"></section>')
        self.captures = self.root / "captures"
        task = {
            "fields": [
                {
                    "name": "REFERENCE",
                    "atoms": ['"artifact/harbour.html"'],
                    "fields": [{"name": "COVERS", "atoms": ['"tides"'], "fields": []}],
                }
            ]
        }
        recipe = {
            "name": "capture",
            "fields": [
                {"name": "SCHEMA_VERSION", "atoms": ['"1"'], "fields": []},
                {
                    "name": "STEP",
                    "atoms": ['"command"'],
                    "fields": [
                        {"name": "ARGV", "atoms": ['"tidepool"'], "fields": []},
                        {"name": "ARGV", "atoms": ['"{page}"'], "fields": []},
                    ],
                },
            ],
        }
        outputs = {
            **TASK_WORKTREE,
            ("git", "rev-parse", "--show-toplevel"): f"{self.worktree}\n",
            ("awawa", "show", "@TASK.T7", "--json", str(self.worktree)): json.dumps(task),
            ("awawa", "status", "--json", str(self.worktree)): json.dumps(
                {"entities": [{"type": "RECIPE", "name": "capture"}]}
            ),
            ("awawa", "show", "@RECIPE.capture", "--json", str(self.worktree)): json.dumps(recipe),
            ("tidepool", "tides"): f"<html><body>{self.paths.home}/tides</body></html>",
        }
        self.runtime = create_test_runtime(
            self.paths, run_process=take_screenshots_or(create_machine_double(TIDEPOOL, outputs))
        )

    def test_should_capture_each_page_the_reference_of_the_task_covers(self):
        # Act
        document = COMMAND.run(Namespace(task="T7", directory=str(self.captures)), self.runtime)

        # Assert
        self.assertEqual(
            document["pages"],
            [
                {
                    "page": "tides",
                    "delivered": str(self.captures / "tides-delivered.png"),
                    "reference": str(self.captures / "tides-reference.png"),
                    "delivered_slices": [str(self.captures / "tides-delivered-01.png")],
                    "reference_slices": [str(self.captures / "tides-reference-01.png")],
                }
            ],
        )

    def test_should_show_the_home_directory_as_a_tilde_in_the_delivered_page(self):
        # Act
        COMMAND.run(Namespace(task="T7", directory=str(self.captures)), self.runtime)

        # Assert
        self.assertEqual((self.captures / "tides-delivered.html").read_text(), "<html><body>~/tides</body></html>")
