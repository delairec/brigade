import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.run_process import ProcessRecord
from brigade.tasks.run_project_checks import ProjectCheck, run_project_checks
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

ROOT = Path("/srv/oak/.brigade/worktrees/integration-dashboard")


class RunProjectChecksTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()

    def test_should_run_each_acceptance_command_then_the_checks_of_the_corpus_whatever_the_others_returned(self):
        # Arrange
        project = Entity(
            name="oak",
            fields=(EntityField(name="PATH", value="/srv/oak"),),
        )
        self.processes.answer_recipes(ROOT, {"acceptance": (("ruff", "check", "."), ("python3", "-m", "unittest"))})
        self.processes.answer(("ruff", "check", "."), exit_code=1, stdout="F401 unused import\n")
        self.processes.answer(("python3", "-m", "unittest"), stderr="OK\n")
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."), exit_code=1, stdout="L025 a mention in prose\n")

        # Act
        checks = run_project_checks(create_test_runtime(run_process=self.processes), project, ROOT)

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

    def test_should_run_only_the_checks_of_the_corpus_when_the_project_has_no_acceptance_recipe(self):
        # Arrange
        project = Entity(name="oak", fields=(EntityField(name="PATH", value="/srv/oak"),))
        no_recipe = {}
        self.processes.answer_recipes(ROOT, no_recipe)
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."))

        # Act
        checks = run_project_checks(create_test_runtime(run_process=self.processes), project, ROOT)

        # Assert
        self.assertEqual(
            checks,
            (
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
                        exit_code=0,
                        stdout="",
                        stderr="",
                        duration_ms=7,
                    ),
                ),
            ),
        )

    def test_should_name_an_acceptance_command_quoting_an_argument_that_holds_a_space(self):
        # Arrange
        project = Entity(name="oak", fields=(EntityField(name="PATH", value="/srv/oak"),))
        self.processes.answer_recipes(ROOT, {"acceptance": (("pytest", "-k", "not slow"),)})
        self.processes.answer(("pytest", "-k", "not slow"))
        self.processes.answer(("awawa", "fmt", "--check", "."))
        self.processes.answer(("awawa", "lint", "--strict", "."))

        # Act
        checks = run_project_checks(create_test_runtime(run_process=self.processes), project, ROOT)

        # Assert
        self.assertEqual(checks[0].command, "pytest -k 'not slow'")


class RunProjectChecksOfAnAreaTest(unittest.TestCase):
    def test_should_check_the_area_and_run_the_acceptance_at_the_root_of_the_worktree(self):
        # Arrange
        processes = ScriptedProcesses()
        project = Entity(
            name="oak",
            fields=(
                EntityField(name="CORPUS", value="brigade"),
                EntityField(name="MODE", value="area"),
            ),
        )
        processes.answer_recipes(ROOT / "brigade", {"acceptance": (("ruff", "check", "."),)})
        processes.answer(("ruff", "check", "."))
        processes.answer(("awawa", "fmt", "--check", "."))
        processes.answer(("awawa", "lint", "--strict", "."))

        # Act
        checks = run_project_checks(create_test_runtime(run_process=processes), project, ROOT)

        # Assert
        self.assertEqual(checks[0].record.cwd, str(ROOT))
        self.assertEqual(checks[1].record.cwd, str(ROOT / "brigade"))
        self.assertEqual(checks[2].record.cwd, str(ROOT / "brigade"))
