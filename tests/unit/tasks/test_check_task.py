import json
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.tasks.check_task import check_task
from brigade.tasks.locate_task_worktree import TaskWorktree
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

PROJECT = Entity(
    name="oak",
    fields=(
        EntityField(name="PATH", value="/srv/oak"),
        EntityField(name="ACCEPTANCE", value="python3 -m unittest"),
        EntityField(name="ACCEPTANCE", value="ruff check ."),
    ),
)
WORKTREE = TaskWorktree(
    path=Path("/srv/oak-b12"), task="B12", project=PROJECT, wave={"branch": "integration/f0-parser"}
)
STATUS_ARGV = ("git", "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all")


class CheckTaskTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()

    def script_checks(self) -> None:
        self.processes.answer(STATUS_ARGV)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="c0ffee\n"
        )
        self.processes.answer(("python3", "-m", "unittest"), stderr="OK\n")
        self.processes.answer(("ruff", "check", "."), exit_code=1, stdout="F401 unused import\n", stderr="1 error\n")
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."))

    def test_should_record_the_verdict_of_each_acceptance_command_and_corpus_check_at_head(self):
        # Arrange
        self.script_checks()
        runtime = create_scripted_runtime(self.root, self.processes)

        # Act
        document = check_task(runtime, WORKTREE)

        # Assert
        recorded = json.loads((self.root / "state" / "checks" / "oak" / "B12.json").read_text(encoding="utf-8"))
        self.assertEqual(
            (document, recorded),
            (
                {
                    "schema_version": 1,
                    "project": "oak",
                    "task": "B12",
                    "head": "c0ffee",
                    "checks": [
                        {"command": "python3 -m unittest", "passed": True, "duration_ms": 7, "tail": []},
                        {
                            "command": "ruff check .",
                            "passed": False,
                            "duration_ms": 7,
                            "tail": ["F401 unused import", "1 error"],
                        },
                        {"command": "awawa fmt --check .", "passed": True, "duration_ms": 7, "tail": []},
                        {"command": "awawa lint --strict .", "passed": True, "duration_ms": 7, "tail": []},
                    ],
                },
                document,
            ),
        )

    def test_should_keep_the_output_of_each_check_in_the_run_directory_of_a_run(self):
        # Arrange
        self.script_checks()
        runtime = create_scripted_runtime(self.root, self.processes, run_directory=self.root / "run")

        # Act
        check_task(runtime, WORKTREE)

        # Assert
        self.assertEqual(
            (self.root / "run" / "check" / "2.log").read_text(encoding="utf-8"), "F401 unused import\n1 error\n"
        )

    def test_should_refuse_a_worktree_holding_changes_head_does_not(self):
        # Arrange
        self.processes.answer(STATUS_ARGV, stdout=" M src/parse.py\0?? notes.md\0")
        runtime = create_scripted_runtime(self.root, self.processes)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_task(runtime, WORKTREE)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the worktree of @TASK.B12 holds changes HEAD does not: src/parse.py, notes.md;"
            " commit them, then run brigade task check",
        )
