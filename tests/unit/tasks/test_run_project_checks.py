import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.system.run_process import ProcessRecord
from brigade.tasks.run_project_checks import ProjectCheck, run_project_checks
from tests.unit.scripted_processes import ScriptedProcesses

ROOT = Path("/srv/oak/.brigade/worktrees/integration-dashboard")


class RunProjectChecksTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()

    def test_should_run_each_acceptance_command_then_the_checks_of_the_corpus_whatever_the_others_returned(self):
        # Arrange
        project = Entity(
            name="oak",
            fields=(
                EntityField(name="PATH", value="/srv/oak"),
                EntityField(name="ACCEPTANCE", value="ruff check ."),
                EntityField(name="ACCEPTANCE", value="python3 -m unittest"),
            ),
        )
        self.processes.answer(("ruff", "check", "."), exit_code=1, stdout="F401 unused import\n")
        self.processes.answer(("python3", "-m", "unittest"), stderr="OK\n")
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."), exit_code=1, stdout="L025 a mention in prose\n")

        # Act
        checks = run_project_checks(self.processes, project, ROOT)

        # Assert
        self.assertEqual(
            checks,
            (
                ProjectCheck(
                    command="ruff check .",
                    record=ProcessRecord(
                        argv=("ruff", "check", "."),
                        cwd="/srv/oak/.brigade/worktrees/integration-dashboard",
                        exit_code=1,
                        stdout="F401 unused import\n",
                        stderr="",
                        duration_ms=7,
                    ),
                ),
                ProjectCheck(
                    command="python3 -m unittest",
                    record=ProcessRecord(
                        argv=("python3", "-m", "unittest"),
                        cwd="/srv/oak/.brigade/worktrees/integration-dashboard",
                        exit_code=0,
                        stdout="",
                        stderr="OK\n",
                        duration_ms=7,
                    ),
                ),
                ProjectCheck(
                    command="awawa fmt --check .",
                    record=ProcessRecord(
                        argv=("awawa", "fmt", "--check", "."),
                        cwd="/srv/oak/.brigade/worktrees/integration-dashboard",
                        exit_code=0,
                        stdout="",
                        stderr="",
                        duration_ms=7,
                    ),
                ),
                ProjectCheck(
                    command="awawa lint --strict .",
                    record=ProcessRecord(
                        argv=("awawa", "lint", "--strict", "."),
                        cwd="/srv/oak/.brigade/worktrees/integration-dashboard",
                        exit_code=1,
                        stdout="L025 a mention in prose\n",
                        stderr="",
                        duration_ms=7,
                    ),
                ),
            ),
        )

    def test_should_refuse_a_line_that_cannot_be_split_by_name_before_any_command_runs(self):
        # Arrange
        project = Entity(
            name="oak",
            fields=(
                EntityField(name="ACCEPTANCE", value="python3 -m unittest"),
                EntityField(name="ACCEPTANCE", value="printf 'oak"),
            ),
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            run_project_checks(self.processes, project, ROOT)

        # Assert
        self.assertEqual(
            str(refusal.exception), "the command printf 'oak cannot be split into an argv: No closing quotation"
        )
        self.assertEqual(self.processes.list_argvs(), [])
