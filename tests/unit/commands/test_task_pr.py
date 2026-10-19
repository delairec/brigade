import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.task_pr import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, create_runtime

THE_TASK_OF_THE_BRANCH = None
MAIN_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/home/user/tidepool\n",
    ("git", "branch", "--show-current"): "main\n",
}


class ForgeDouble:
    def describe_account(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "login": "tidepool-bot"}


def _resolve_the_forge_double(kind: str, name: str, **places):
    return ForgeDouble()


class TaskPrTextTest(unittest.TestCase):
    def test_should_print_the_address_of_the_pull_request(self):
        # Act
        text = COMMAND.render_text({"url": "https://github.com/user/tidepool/pull/42"})

        # Assert
        self.assertEqual(text, "https://github.com/user/tidepool/pull/42")


class TaskPrExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"url": "https://github.com/user/tidepool/pull/42"})

        # Assert
        self.assertEqual(exit_code, 0)


class TaskPrRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(task=None, subject=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class TaskPrOutsideATaskTest(unittest.TestCase):
    def test_should_refuse_a_branch_that_is_not_the_branch_of_a_task(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text('attribution = ["Co-Authored-By: a model"]\n', encoding="utf-8")
        runtime = create_runtime(
            root,
            run_process=create_machine_double({}, MAIN_BRANCH_CHECKOUT),
            resolve_plugin=_resolve_the_forge_double,
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(task=THE_TASK_OF_THE_BRANCH, subject=None), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the branch main is not a task/<slug>/<task> branch")
