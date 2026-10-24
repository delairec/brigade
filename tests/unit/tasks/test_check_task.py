import json
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.tasks.check_task import check_task
from brigade.tasks.locate_task_worktree import TaskWorktree
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
    path=Path("/srv/oak-b12"), task="B12", project=PROJECT, wave="oak_w1", wave_branch="integration/oak_w1"
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

STATUS_ARGV = ("git", "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all")
CHECK = {
    "schema_version": 1,
    "project": "oak",
    "task": "B12",
    "head": "c0ffee",
    "checks": [
        {"command": "python3 -m unittest", "passed": True, "duration_ms": 7, "tail": []},
        {"command": "ruff check .", "passed": False, "duration_ms": 7, "tail": ["F401 unused import", "1 error"]},
        {"command": "awawa fmt --check .", "passed": True, "duration_ms": 7, "tail": []},
        {"command": "awawa lint --strict .", "passed": True, "duration_ms": 7, "tail": []},
    ],
}


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

    def test_should_answer_the_verdict_of_each_acceptance_command_and_corpus_check_at_head(self):
        # Arrange
        self.script_checks()

        # Act
        document = check_task(create_test_runtime(create_test_paths(self.root), run_process=self.processes), WORKTREE)

        # Assert
        self.assertEqual(document, CHECK)

    def test_should_record_the_check_of_the_task(self):
        # Arrange
        self.script_checks()

        # Act
        check_task(create_test_runtime(create_test_paths(self.root), run_process=self.processes), WORKTREE)

        # Assert
        record = self.root / "state" / "checks" / "oak" / "B12.json"
        self.assertEqual(json.loads(record.read_text(encoding="utf-8")), CHECK)

    def test_should_keep_the_output_of_each_check_in_the_run_directory_of_a_run(self):
        # Arrange
        self.script_checks()
        write_operational_corpus(self.root)
        runtime = create_test_runtime(
            create_test_paths(self.root, run_directory=self.root / "run"), run_process=self.processes
        )

        # Act
        check_task(runtime, WORKTREE)

        # Assert
        self.assertEqual(
            (self.root / "run" / "check" / "2.log").read_text(encoding="utf-8"), "F401 unused import\n1 error\n"
        )

    def test_should_refuse_a_worktree_holding_changes_head_does_not(self):
        # Arrange
        self.processes.answer(STATUS_ARGV, stdout=" M src/parse.py\0?? notes.md\0")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_task(create_test_runtime(create_test_paths(self.root), run_process=self.processes), WORKTREE)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the worktree of @TASK.B12 holds changes HEAD does not: src/parse.py, notes.md;"
            " commit them, then run brigade task check",
        )


class CheckTaskOfAFailingCommandWithALongOutputTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()

    def test_should_keep_the_last_twenty_lines_of_its_output(self):
        # Arrange
        self.processes.answer(STATUS_ARGV)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="c0ffee\n"
        )
        self.processes.answer(
            ("python3", "-m", "unittest"),
            exit_code=1,
            stdout="line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8\nline 9\nline 10\nline 11\n"
            "line 12\nline 13\nline 14\nline 15\nline 16\nline 17\nline 18\nline 19\nline 20\nline 21\n"
            "line 22\nline 23\nline 24\nline 25\n",
        )
        self.processes.answer(("ruff", "check", "."))
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."))

        # Act
        document = check_task(create_test_runtime(create_test_paths(self.root), run_process=self.processes), WORKTREE)

        # Assert
        self.assertEqual(
            document["checks"][0]["tail"],
            [
                "line 6",
                "line 7",
                "line 8",
                "line 9",
                "line 10",
                "line 11",
                "line 12",
                "line 13",
                "line 14",
                "line 15",
                "line 16",
                "line 17",
                "line 18",
                "line 19",
                "line 20",
                "line 21",
                "line 22",
                "line 23",
                "line 24",
                "line 25",
            ],
        )


class CheckTaskOfALineThatCannotBeSplitTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        project = Entity(
            name="oak",
            fields=(
                EntityField(name="PATH", value="/srv/oak"),
                EntityField(name="ACCEPTANCE", value="python3 -m unittest"),
                EntityField(name="ACCEPTANCE", value="printf 'oak"),
            ),
        )
        self.worktree = TaskWorktree(
            path=Path("/srv/oak-b12"), task="B12", project=project, wave="oak_w1", wave_branch="integration/oak_w1"
        )

    def test_should_refuse_the_line_by_name_before_any_command_runs(self):
        # Arrange
        self.processes.answer(STATUS_ARGV)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_task(create_test_runtime(create_test_paths(self.root), run_process=self.processes), self.worktree)

        # Assert
        self.assertEqual(
            str(refusal.exception), "the command printf 'oak cannot be split into an argv: No closing quotation"
        )
        self.assertEqual(self.processes.list_argvs(), [STATUS_ARGV])
