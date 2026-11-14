import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.task_push import COMMAND
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_started import WaveStarted
from tests.unit.commands.command_runtime import NOW, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

THE_TASK_OF_THE_BRANCH = None
BOUND_ACCOUNTS = '[forge_accounts]\nbuild = "octo-bot"\nreview = "rev-bot"\n'
PASSING_CHECK = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "d00d",'
    ' "checks": [{"command": "python3 -m unittest", "passed": true, "duration_ms": 1200, "tail": []}]}'
)


def _answer_the_token_of_the_login(request: dict) -> dict:
    return {"schema_version": 1, "environment": {"GH_TOKEN": f"token-of-{request['login']}"}}


class TaskPushTextTest(unittest.TestCase):
    def test_should_name_the_branch_pushed_and_its_head(self):
        # Act
        text = COMMAND.render_text({"task": "T7", "branch": "feature/T7-the-cart", "head": "8885daa"})

        # Assert
        self.assertEqual(text, "feature/T7-the-cart pushed at 8885daa for @TASK.T7")


class TaskPushAsTheBuildSlotTest(unittest.TestCase):
    def test_should_push_the_branch_as_the_login_of_the_build_slot(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        worktree = root / "oak-b12"
        worktree.mkdir()
        write_operational_corpus(root)
        (root / "config" / "config.toml").write_text(BOUND_ACCOUNTS, encoding="utf-8")
        record = root / "state" / "checks" / "oak" / "B12.json"
        record.parent.mkdir(parents=True)
        record.write_text(PASSING_CHECK, encoding="utf-8")
        processes = ScriptedProcesses()
        forge = ForgeDouble({"read_login_environment": _answer_the_token_of_the_login})
        runtime = create_test_runtime(
            create_test_paths(root), run_process=processes, resolve_plugin=lambda kind, name, **places: forge
        )
        processes.answer(("git", "rev-parse", "--show-toplevel"), stdout=f"{worktree}\n")
        processes.answer(("git", "branch", "--show-current"), stdout="feature/B12-the-parser\n")
        processes.answer(("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n")
        processes.answer_entities(
            runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"), ("FORGE", "github"))}
        )
        processes.answer_entity(worktree, "TASK", "B12", (("TITLE", "The parser"),))
        processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="d00d\n"
        )
        processes.answer(("git", "rev-parse", "--verify", "--quiet", "refs/remotes/origin/feature/B12-the-parser"))
        pushed_environments = []

        def record_push(request):
            pushed_environments.append(request.environment)
            return 0, "", ""

        processes.answer_by(
            (
                "git",
                "push",
                "--quiet",
                "--force-with-lease=feature/B12-the-parser:",
                "origin",
                "feature/B12-the-parser",
            ),
            record_push,
        )
        append_event(runtime.paths, NOW, WaveStarted(wave="oak_w1", project="oak", tasks=("B12",)))

        # Act
        COMMAND.run(Namespace(task=THE_TASK_OF_THE_BRANCH), runtime)

        # Assert
        self.assertEqual(pushed_environments, [{"GH_TOKEN": "token-of-octo-bot"}])
