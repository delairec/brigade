import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.task_promote import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.plugin_double import PluginDouble

THE_TASK_OF_THE_BRANCH = None
THE_LAST_PULL_REQUEST = None
MAIN_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/home/user/tidepool\n",
    ("git", "branch", "--show-current"): "main\n",
}


def _resolve_a_forge(kind: str, name: str, **places):
    return PluginDouble(kind=kind, name=name)


class TaskPromoteTextTest(unittest.TestCase):
    def test_should_name_the_pull_request_and_the_commit_of_the_promotion(self):
        # Act
        text = COMMAND.render_text({"task": "T7", "pr": 42, "commit": "8885daa"})

        # Assert
        self.assertEqual(text, "@TASK.T7 implemented, delivered by #42, in 8885daa")


class TaskPromoteExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"task": "T7", "pr": 42, "commit": "8885daa"})

        # Assert
        self.assertEqual(exit_code, 0)


class TaskPromoteRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(task=None, pr=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class TaskPromoteOutsideATaskTest(unittest.TestCase):
    def test_should_refuse_a_branch_that_is_not_the_branch_of_a_task(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text('attribution = ["Co-Authored-By: a model"]\n', encoding="utf-8")
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_machine_double({}, MAIN_BRANCH_CHECKOUT),
            resolve_plugin=_resolve_a_forge,
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH, pr=THE_LAST_PULL_REQUEST), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the branch main is not a task/<slug>/<task> branch")
