import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.task_pr import COMMAND
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_started import WaveStarted
from tests.unit.commands.command_runtime import NOW, create_machine_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

THE_TASK_OF_THE_BRANCH = None
MAIN_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/home/user/tidepool\n",
    ("git", "branch", "--show-current"): "main\n",
}
BOUND_ACCOUNTS = (
    'attribution = ["Co-Authored-By: Ada <ada@example.org>"]\n'
    '[forge_accounts]\nbuild = "octo-bot"\nreview = "rev-bot"\n'
)
PASSING_CHECK = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "d00d",'
    ' "checks": [{"command": "python3 -m unittest", "passed": true, "duration_ms": 1200, "tail": []}]}'
)
TASK_FIELDS = (
    ("TYPE", "feat"),
    ("COMPONENT", "the parser"),
    ("TITLE", "The parser"),
    ("SPEC", "parses a line"),
    ("MILESTONE", "@MILESTONE.F0"),
)
OPENED_PULL_REQUEST = {"number": 42, "url": "https://github.com/acme/oak/pull/42"}


ACCOUNT = {"schema_version": 1, "login": "tidepool-bot"}


def _resolve_the_forge_double(kind: str, name: str, **places):
    return ForgeDouble({"describe_account": lambda request: ACCOUNT})


def _answer_the_token_of_the_login(request: dict) -> dict:
    return {"schema_version": 1, "environment": {"GH_TOKEN": f"token-of-{request['login']}"}}


def _answer_the_login_of_the_token(request: dict) -> dict:
    return {"schema_version": 1, "login": request["environment"]["GH_TOKEN"].removeprefix("token-of-")}


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
        options = Namespace(task=None, subject=None)

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
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_machine_double({}, MAIN_BRANCH_CHECKOUT),
            resolve_plugin=_resolve_the_forge_double,
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH, subject=None), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the branch main is not a task/<slug>/<task> branch")


class TaskPrPushTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        worktree = Path("/srv/oak-b12")
        write_operational_corpus(root)
        (root / "config" / "config.toml").write_text(BOUND_ACCOUNTS, encoding="utf-8")
        (root / "state" / "checks" / "oak").mkdir(parents=True)
        (root / "state" / "checks" / "oak" / "B12.json").write_text(PASSING_CHECK, encoding="utf-8")
        self.processes = ScriptedProcesses()
        self.forge = ForgeDouble(
            {
                "read_login_environment": _answer_the_token_of_the_login,
                "describe_account": _answer_the_login_of_the_token,
                "list_milestones": lambda request: {"titles": ["Parser"]},
                "open_pull_request": lambda request: OPENED_PULL_REQUEST,
            }
        )
        self.runtime = create_test_runtime(
            create_test_paths(root), run_process=self.processes, resolve_plugin=lambda kind, name, **places: self.forge
        )
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout=f"{worktree}\n")
        self.processes.answer(("git", "branch", "--show-current"), stdout="task/oak_w1/B12\n")
        self.processes.answer(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n"
        )
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
        append_event(
            self.runtime.paths,
            NOW,
            WaveStarted(wave="oak_w1", project="oak", branch="integration/oak_w1", tasks=("B12",)),
        )
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="d00d\n"
        )
        self.processes.answer_entity(worktree, "TASK", "B12", TASK_FIELDS)
        self.processes.answer_entity(worktree, "MILESTONE", "F0", (("TITLE", "Parser"),))
        self.pushed_environments = []
        self.processes.answer_by(("git", "push", "--quiet", "origin", "task/oak_w1/B12"), self.record_push)

    def record_push(self, request):
        self.pushed_environments.append(request.environment)
        return 0, "", ""

    def test_should_push_the_task_branch_as_the_login_of_the_build_slot(self):
        # Act
        COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH, subject="add the parser"), self.runtime)

        # Assert
        self.assertEqual(self.pushed_environments, [{"GH_TOKEN": "token-of-octo-bot"}])

    def test_should_open_the_pull_request_as_the_login_of_the_build_slot(self):
        # Act
        opened = COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH, subject="add the parser"), self.runtime)

        # Assert
        self.assertEqual(opened["login"], "octo-bot")

    def test_should_close_the_body_on_the_attribution_of_the_configuration(self):
        # Act
        COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH, subject="add the parser"), self.runtime)

        # Assert
        (opening,) = self.forge.list_requests("open_pull_request")
        self.assertEqual(opening["body"].splitlines()[-1], "Co-Authored-By: Ada <ada@example.org>")
