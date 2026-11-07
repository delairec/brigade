import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.tick.actions import RebaseTask
from brigade.tick.rebase_task import rebase_task
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

WORKTREE = "/srv/shop/.brigade/worktrees/B1"
WAVE_HEAD = "9a8b7c6"
ACTION = RebaseTask(
    project="shop",
    wave="w1",
    branch="integration/w1",
    task="B1",
    task_branch="feature/B1-task",
    pr=12,
    worktree=WORKTREE,
    head="5c1d2e0",
    holds_uncommitted_changes=False,
)
REBASE_ONTO_THE_WAVE_BRANCH = ("git", "rebase", "--fork-point", "origin/integration/w1")
CLI_ENVIRONMENT = {"GH_TOKEN": "token-of-the-cli"}


class CheckRunsForgeDouble:
    def __init__(self, check_runs: list[dict]):
        self.check_runs = check_runs

    def list_check_runs(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "check_runs": self.check_runs}


def resolve_the_forge(forge: CheckRunsForgeDouble):
    def resolve_plugin(kind: str, name: str):
        if (kind, name) != ("forge", "github"):
            raise AssertionError(f"the {kind} plugin {name} should not be resolved")
        return forge

    return resolve_plugin


class RebaseTaskBehindAWaveBranchOfTheForgeTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        self.paths = create_test_paths(root)
        record = self.paths.state_root / "commit-checks" / "shop" / f"{WAVE_HEAD}.json"
        record.parent.mkdir(parents=True)
        record.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project": "shop",
                    "commit": WAVE_HEAD,
                    "checks": [{"command": "make test", "exit_code": 1}],
                }
            ),
            encoding="utf-8",
        )
        self.runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": "/srv/shop", "FORGE": "github"}}),
                (
                    "git",
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    "--end-of-options",
                    "origin/integration/w1^{commit}",
                ): ProcessAnswer(stdout=f"{WAVE_HEAD}\n"),
            }
        )

    def test_should_rebase_once_the_check_runs_of_the_forge_passed_on_the_head_of_the_wave_branch(self):
        # Arrange
        forge = CheckRunsForgeDouble(
            [
                {
                    "pull_request": None,
                    "branch": "integration/w1",
                    "head": WAVE_HEAD,
                    "name": "unit",
                    "conclusion": "success",
                    "link": "https://github.com/delairec/shop/actions/runs/1/job/2",
                }
            ]
        )
        runtime = create_test_runtime(self.paths, run_process=self.runner, resolve_plugin=resolve_the_forge(forge))

        # Act
        rebase_task(runtime, ACTION, CLI_ENVIRONMENT)

        # Assert
        self.assertIn((WORKTREE, REBASE_ONTO_THE_WAVE_BRANCH), self.runner.commands)
