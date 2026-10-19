import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError, CorpusLintFailed
from brigade.ledger.append_event import append_event
from brigade.ledger.plan_lint_failed import PlanLintFailed
from brigade.ledger.read_ledger import read_ledger
from brigade.planning.read_planning_request import PlanningRequest
from brigade.planning.record_plan import PlanRecording, record_plan
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

PLAN = 'MILESTONE F1\n\tTITLE "Printer"\n\nTASK B20\n\tTITLE "the printer"\n\tMILESTONE @MILESTONE.F1\n'
BRANCH = "integration/F1-printer"
SKELETONS = {"MILESTONE": 'MILESTONE F1\n\tTITLE ""\n', "TASK": 'TASK B20\n\tTITLE ""\n\tMILESTONE @MILESTONE.X\n'}


class RecordPlanFixture(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.plan_file = self.root / "plan.awawa"
        self.plan_file.write_text(PLAN, encoding="utf-8")
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes, run_directory=self.root / "runs" / "r1")
        self.worktree = self.root / "cache" / "plans" / "oak_1"
        (self.worktree / "corpus").mkdir(parents=True)
        (self.worktree / "corpus" / "tasks.awawa").write_text('TASK B19\n\tTITLE "the parser"\n', encoding="utf-8")
        self.config_root = self.runtime.paths.config_root
        (self.config_root / "requests.awawa").write_text("REQUEST oak_1\n\tSTATUS planning\n", encoding="utf-8")
        self.processes.answer(("git", "worktree", "add", "--quiet", "--detach", str(self.worktree), "main"))
        self.processes.answer(("git", "worktree", "remove", "--force", str(self.worktree)))

    def script_plan(self, entities: list[tuple[str, str, tuple]]) -> None:
        plan_file = str(self.plan_file)
        self.processes.answer_json(
            ("awawa", "show", plan_file, "--json", plan_file),
            {"entities": [{"type": entity_type, "name": name} for entity_type, name, fields in entities]},
        )
        for entity_type, name, fields in entities:
            self.processes.answer_json(
                ("awawa", "show", f"@{entity_type}.{name}", "--json", plan_file),
                {"fields": [{"name": field, "atoms": [value]} for field, value in fields]},
            )

    def script_corpus(self, sites: list[dict]) -> None:
        self.processes.answer_json(("awawa", "status", "--json", str(self.worktree)), {"entities": sites})
        self.processes.answer(("awawa", "new", "MILESTONE", "F1", str(self.worktree)), stdout=SKELETONS["MILESTONE"])
        self.processes.answer(("awawa", "new", "TASK", "B20", str(self.worktree)), stdout=SKELETONS["TASK"])

    def script_valid_plan(self) -> None:
        self.script_plan(
            [
                ("MILESTONE", "F1", (("TITLE", '"Printer"'),)),
                ("TASK", "B20", (("TITLE", '"the printer"'), ("MILESTONE", "@MILESTONE.F1"))),
            ]
        )
        self.script_corpus([{"type": "TASK", "name": "B19", "file": "corpus/tasks.awawa", "line": 1}])
        self.processes.answer(("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}"), exit_code=1)

    def script_recording(self) -> None:
        self.script_valid_plan()
        self.processes.answer_corpus_change(
            self.worktree, ("corpus/milestones.awawa", "corpus/tasks.awawa"), f"brigade plan record: {BRANCH}"
        )
        self.processes.answer(("git", "switch", "--quiet", "--create", BRANCH))
        self.processes.answer(("git", "push", "--quiet", "origin", BRANCH))
        self.processes.answer_json(
            ("awawa", "status", "--json", str(self.config_root)),
            {"entities": [{"type": "REQUEST", "name": "oak_1", "file": "requests.awawa", "line": 1}]},
        )
        self.processes.answer_corpus_change(
            self.config_root, ("requests.awawa",), f"brigade plan record: @REQUEST.oak_1 planned on {BRANCH}"
        )

    def create_recording(self, forge: str = "github") -> PlanRecording:
        project = Entity(
            name="oak",
            fields=(
                EntityField(name="PATH", value="/srv/oak"),
                EntityField(name="MAIN", value="main"),
                EntityField(name="CORPUS", value="corpus"),
                EntityField(name="FORGE", value=forge),
            ),
        )
        return PlanRecording(
            request=PlanningRequest(name="oak_1", project="oak", text="print"),
            project=project,
            plan_file=self.plan_file,
        )

    def read_refusal(self) -> str:
        with self.assertRaises(BrigadeError) as refusal:
            record_plan(self.runtime, self.create_recording())
        return str(refusal.exception)


class RecordPlanTest(RecordPlanFixture):
    def test_should_record_the_plan_on_the_integration_branch_of_its_milestone(self):
        # Arrange
        self.script_recording()

        # Act
        recorded = record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(recorded, {"request": "oak_1", "milestone": "F1", "branch": BRANCH})

    def test_should_append_each_planned_entity_to_the_corpus_file_of_its_type(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            (
                (self.worktree / "corpus" / "milestones.awawa").read_text(encoding="utf-8"),
                (self.worktree / "corpus" / "tasks.awawa").read_text(encoding="utf-8"),
            ),
            (
                'MILESTONE F1\n\tTITLE "Printer"\n',
                'TASK B19\n\tTITLE "the parser"\n\nTASK B20\n\tTITLE "the printer"\n\tMILESTONE @MILESTONE.F1\n',
            ),
        )

    def test_should_mark_the_request_planned_on_the_branch(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            (self.config_root / "requests.awawa").read_text(encoding="utf-8"),
            f'REQUEST oak_1\n\tSTATUS planned\n\tMILESTONE "F1"\n\tBRANCH "{BRANCH}"\n',
        )

    def test_should_push_the_branch_of_a_project_on_github(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording("github"))

        # Assert
        self.assertIn(("git", "push", "--quiet", "origin", BRANCH), self.processes.list_argvs())

    def test_should_keep_the_branch_of_a_project_without_a_forge_local(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording("none"))

        # Assert
        self.assertNotIn(("git", "push", "--quiet", "origin", BRANCH), self.processes.list_argvs())

    def test_should_remove_the_worktree_the_plan_was_checked_in(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertIn(("git", "worktree", "remove", "--force", str(self.worktree)), self.processes.list_argvs())


class RecordPlanLintTest(RecordPlanFixture):
    def script_refused_lint(self) -> None:
        self.script_valid_plan()
        files = ("corpus/milestones.awawa", "corpus/tasks.awawa")
        self.processes.answer_corpus_change(self.worktree, files, "unused", lint_output="L012 dangling reference")
        self.processes.answer(("git", "ls-tree", "--name-only", "HEAD", "--", *files), stdout="corpus/tasks.awawa\n")
        self.processes.answer(("git", "checkout", "HEAD", "--", "corpus/tasks.awawa"))
        self.processes.answer(("git", "rm", "--cached", "--quiet", "--ignore-unmatch", "--", "corpus/milestones.awawa"))
        self.processes.answer(("git", "clean", "--force", "--quiet", "--", "corpus/milestones.awawa"))

    def test_should_record_the_lint_round_the_plan_spent(self):
        # Arrange
        self.script_refused_lint()

        # Act
        with self.assertRaises(CorpusLintFailed):
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(read_ledger(self.root / "state").entries[-1].event, PlanLintFailed(request="oak_1", run="r1"))

    def test_should_record_the_lint_round_of_a_recording_outside_a_run_with_no_run(self):
        # Arrange
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.script_refused_lint()

        # Act
        with self.assertRaises(CorpusLintFailed):
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(read_ledger(self.root / "state").entries[-1].event, PlanLintFailed(request="oak_1", run=None))

    def test_should_refuse_a_second_lint_round_in_the_same_run(self):
        # Arrange
        append_event(
            self.runtime.paths, datetime(2026, 10, 19, 8, 0, tzinfo=UTC), PlanLintFailed(request="oak_1", run="r1")
        )

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "@REQUEST.oak_1 spent its lint round in run r1; the run ends blocked")


class RecordPlanRefusalTest(RecordPlanFixture):
    def test_should_refuse_a_planned_entity_the_corpus_already_holds(self):
        # Arrange
        self.script_plan([("TASK", "B19", (("TITLE", '"again"'),))])
        self.processes.answer_json(
            ("awawa", "status", "--json", str(self.worktree)),
            {"entities": [{"type": "TASK", "name": "B19", "file": "corpus/tasks.awawa", "line": 1}]},
        )

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "@TASK.B19 already exists at corpus/tasks.awawa:1")

    def test_should_refuse_a_planned_field_the_schema_does_not_declare(self):
        # Arrange
        self.script_plan([("MILESTONE", "F1", (("TITLE", '"Printer"'), ("OWNER", '"ada"')))])
        self.script_corpus([])

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(
            message, "the schema of the corpus of @PROJECT.oak does not declare the field OWNER of MILESTONE"
        )

    def test_should_refuse_a_plan_holding_neither_a_milestone_nor_a_task(self):
        # Arrange
        self.script_plan([("DECISION", "D9", ())])
        self.processes.answer_json(("awawa", "status", "--json", str(self.worktree)), {"entities": []})
        self.processes.answer(("awawa", "new", "DECISION", "D9", str(self.worktree)), stdout="DECISION D9\n")

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "the plan holds @DECISION.D9, which is neither a MILESTONE nor a TASK")

    def test_should_refuse_a_plan_without_exactly_one_milestone(self):
        # Arrange
        self.script_plan([("TASK", "B20", (("TITLE", '"the printer"'),))])
        self.script_corpus([])

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "the plan holds 0 MILESTONE entities, not one")

    def test_should_refuse_a_task_planned_on_another_milestone(self):
        # Arrange
        self.script_plan(
            [
                ("MILESTONE", "F1", (("TITLE", '"Printer"'),)),
                ("TASK", "B20", (("TITLE", '"the printer"'), ("MILESTONE", "@MILESTONE.F0"))),
            ]
        )
        self.script_corpus([])

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "the plan holds @TASK.B20, whose MILESTONE is not @MILESTONE.F1")

    def test_should_refuse_a_milestone_whose_branch_already_exists(self):
        # Arrange
        self.script_valid_plan()
        self.processes.answer(("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}"), stdout="c0ffee\n")

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, f"the branch {BRANCH} already exists")
