import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.task_promote import COMMAND
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_started import WaveStarted
from tests.unit.commands.command_runtime import NOW, create_machine_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.plugin_double import PluginDouble
from tests.unit.scripted_processes import ScriptedProcesses

THE_TASK_OF_THE_BRANCH = None
THE_LAST_PULL_REQUEST = None
MAIN_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/home/user/tidepool\n",
    ("git", "branch", "--show-current"): "main\n",
}

BOUND_ACCOUNTS = (
    'attribution = ["Co-Authored-By: Ada <ada@example.org>"]\n'
    '[forge_accounts]\nbuild = "octo-bot"\nreview = "rev-bot"\n'
)
MESSAGE = "docs(corpus): mark @TASK.B12 implemented, delivered by #42\n\nCo-Authored-By: Ada <ada@example.org>"


def _answer_the_token_of_the_login(request: dict) -> dict:
    return {"schema_version": 1, "environment": {"GH_TOKEN": f"token-of-{request['login']}"}}


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


class TaskPromotePushTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        worktree = root / "oak-b12"
        (worktree / "corpus").mkdir(parents=True)
        (worktree / "corpus" / "tasks.awawa").write_text("TASK B12\n\tSTATUS todo\n", encoding="utf-8")
        write_operational_corpus(root)
        (root / "config" / "config.toml").write_text(BOUND_ACCOUNTS, encoding="utf-8")
        self.processes = ScriptedProcesses()
        forge = ForgeDouble({"read_login_environment": _answer_the_token_of_the_login})
        self.runtime = create_test_runtime(
            create_test_paths(root), run_process=self.processes, resolve_plugin=lambda kind, name, **places: forge
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
        self.processes.answer_json(
            ("awawa", "show", "TASK", "--json", str(worktree)),
            {
                "fields": [
                    {"name": "FIELD", "atoms": ["STATUS", "todo|implemented"]},
                    {"name": "FIELD", "atoms": ["DELIVERED_BY", "uint"]},
                ]
            },
        )
        self.processes.answer_json(
            ("awawa", "show", "@TASK.B12", "--json", str(worktree)), {"file": str(worktree / "corpus" / "tasks.awawa")}
        )
        self.processes.answer_corpus_change(worktree, ("corpus/tasks.awawa",), MESSAGE)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="d00d\n"
        )

    def test_should_push_the_promotion_as_the_login_of_the_build_slot(self):
        # Arrange
        pushed_environments = []

        def record_push(request):
            pushed_environments.append(request.environment)
            return 0, "", ""

        self.processes.answer_by(("git", "push", "--quiet", "origin", "task/oak_w1/B12"), record_push)

        # Act
        COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH, pr=42), self.runtime)

        # Assert
        self.assertEqual(pushed_environments, [{"GH_TOKEN": "token-of-octo-bot"}])
