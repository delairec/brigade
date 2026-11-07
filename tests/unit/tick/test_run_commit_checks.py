import json
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.tick.commit_checks import CommandResult, CommitChecks
from brigade.tick.run_commit_checks import run_commit_checks
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

CHECKOUT = Path("/srv/oak/.brigade/worktrees/check-c0ffee")
PROJECT = Entity(
    name="oak",
    fields=(
        EntityField(name="PATH", value="/srv/oak"),
        EntityField(name="SETUP", value="npm ci"),
        EntityField(name="ACCEPTANCE", value="npm test"),
    ),
)


class RunCommitChecksTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.processes.answer(("npm", "ci"))
        self.processes.answer(("npm", "test"), exit_code=1)
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."))

    def test_should_run_the_setup_lines_then_the_acceptance_lines_then_the_checks_of_the_corpus(self):
        # Act
        run_commit_checks(self.runtime, PROJECT, CHECKOUT, "c0ffee")

        # Assert
        self.assertEqual(
            self.processes.list_argvs(),
            [("npm", "ci"), ("npm", "test"), ("awawa", "fmt", "--check", "."), ("awawa", "lint", "--strict", ".")],
        )

    def test_should_return_each_command_of_the_commit_with_its_exit_code(self):
        # Act
        checks = run_commit_checks(self.runtime, PROJECT, CHECKOUT, "c0ffee")

        # Assert
        self.assertEqual(
            checks,
            CommitChecks(
                project="oak",
                commit="c0ffee",
                results=(
                    CommandResult(command="npm ci", exit_code=0),
                    CommandResult(command="npm test", exit_code=1),
                    CommandResult(command="awawa fmt --check .", exit_code=0),
                    CommandResult(command="awawa lint --strict .", exit_code=0),
                ),
            ),
        )

    def test_should_write_the_record_under_the_state_root_by_project_and_commit(self):
        # Act
        run_commit_checks(self.runtime, PROJECT, CHECKOUT, "c0ffee")

        # Assert
        record = self.runtime.paths.state_root / "commit-checks" / "oak" / "c0ffee.json"
        self.assertEqual(
            json.loads(record.read_text(encoding="utf-8")),
            {
                "schema_version": 1,
                "project": "oak",
                "commit": "c0ffee",
                "checks": [
                    {"command": "npm ci", "exit_code": 0},
                    {"command": "npm test", "exit_code": 1},
                    {"command": "awawa fmt --check .", "exit_code": 0},
                    {"command": "awawa lint --strict .", "exit_code": 0},
                ],
            },
        )
