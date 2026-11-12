import json
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import ToolFailure
from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRequest
from brigade.tick.head_proof import HeadProof, TaskCheck
from brigade.tick.prove_head import HeadQuery, prove_head
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

PROJECT = Entity(
    name="oak",
    fields=(
        EntityField(name="PATH", value="/srv/oak"),
        EntityField(name="ACCEPTANCE", value="npm test"),
    ),
)
REPOSITORY = Path("/srv/oak")
NO_FORGE_CHECK = ()


def stop_on_a_timeout(request):
    raise ToolFailure("npm test timed out after 1800 s")


NO_TASK_CHECK = None


class ProveHeadTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.paths = create_test_paths(Path(directory.name))
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(self.paths, run_process=self.processes)
        self.checkout = self.paths.state_root / "head-checks" / "oak" / "c0ffee"

    def write_record(self, relative: str, document: dict) -> None:
        record = self.paths.state_root / relative
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps(document), encoding="utf-8")

    def answer_the_checks_on_a_checkout(self, test_exit_code: int) -> None:
        self.processes.answer(("git", "worktree", "add", "--quiet", "--detach", str(self.checkout), "c0ffee"))
        self.processes.answer(("npm", "test"), exit_code=test_exit_code)
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."))
        self.processes.answer(("git", "worktree", "remove", "--force", str(self.checkout)))

    def test_should_prove_green_a_commit_whose_record_by_sha_holds_every_command_passed_running_nothing(self):
        # Arrange
        self.write_record(
            "commit-checks/oak/c0ffee.json",
            {
                "schema_version": 1,
                "project": "oak",
                "commit": "c0ffee",
                "checks": [{"command": "npm test", "exit_code": 0}],
            },
        )

        # Act
        proof = prove_head(self.runtime, HeadQuery(PROJECT, REPOSITORY, "c0ffee", NO_TASK_CHECK, NO_FORGE_CHECK))

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="green", failed_commands=()))
        self.assertEqual(self.processes.list_argvs(), [])

    def test_should_prove_red_a_commit_the_task_check_holds_with_a_failed_command(self):
        # Arrange
        task_check = TaskCheck(head="c0ffee", failed_commands=("npm test",))

        # Act
        proof = prove_head(self.runtime, HeadQuery(PROJECT, REPOSITORY, "c0ffee", task_check, NO_FORGE_CHECK))

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="red", failed_commands=("npm test",)))

    def test_should_check_an_unproven_commit_on_a_checkout_of_its_own_and_judge_it_by_the_result(self):
        # Arrange
        self.answer_the_checks_on_a_checkout(test_exit_code=1)

        # Act
        proof = prove_head(self.runtime, HeadQuery(PROJECT, REPOSITORY, "c0ffee", NO_TASK_CHECK, NO_FORGE_CHECK))

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="red", failed_commands=("npm test",)))

    def test_should_remove_the_checkout_of_an_unproven_commit_once_checked(self):
        # Arrange
        self.answer_the_checks_on_a_checkout(test_exit_code=0)

        # Act
        prove_head(self.runtime, HeadQuery(PROJECT, REPOSITORY, "c0ffee", NO_TASK_CHECK, NO_FORGE_CHECK))

        # Assert
        self.assertEqual(
            self.processes.requests[-1],
            ProcessRequest(
                argv=("git", "worktree", "remove", "--force", str(self.checkout)),
                cwd="/srv/oak",
                timeout_s=TREE_TIMEOUT_S,
            ),
        )

    def test_should_remove_the_checkout_of_an_unproven_commit_whose_check_stopped_on_an_error(self):
        # Arrange
        self.answer_the_checks_on_a_checkout(test_exit_code=0)
        self.processes.answer_by(("npm", "test"), stop_on_a_timeout)

        # Act
        with self.assertRaises(ToolFailure):
            prove_head(self.runtime, HeadQuery(PROJECT, REPOSITORY, "c0ffee", NO_TASK_CHECK, NO_FORGE_CHECK))

        # Assert
        self.assertEqual(self.processes.requests[-1].argv, ("git", "worktree", "remove", "--force", str(self.checkout)))
