import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.documents import markdown
from brigade.adapters.test_clients import fake
from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError, UsageError
from brigade.ledger.budget_applied import BudgetApplied
from brigade.ledger.describe_role_budget import RoleBudget
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.plan_run import RunPlan, RunPlugins, RunRequest, plan_run
from brigade.runs.read_run_setting import RunSetting
from brigade.runs.resolve_procedure import Procedure
from brigade.system.parse_configuration import Configuration
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.runs.create_run_plan import CAP_OF_FORTY_STEPS
from tests.unit.runs.mason_segments import (
    EARLIER_MASON_BUDGET_APPLIED,
    MASON_BUDGET_APPLIED,
    MASON_ROLE,
    MASON_SEGMENTS,
    STONEMASON_BUDGET_APPLIED,
    STONEMASON_ROLE,
    SURVEY_PROCEDURE,
)
from tests.unit.runs.write_run_result import write_run_result

NO_ARGUMENTS = {}
NO_WAVE = None
NO_TASK = None
NO_BRIEF = None
NO_WARNINGS = ()
NO_HANDOVER = 0


class RunPlanOfASlotBoundToALoginTest(unittest.TestCase):
    def test_should_keep_the_token_of_the_login_out_of_its_representation(self):
        # Arrange
        plan = RunPlan(
            run_id="20261009T120000Z-b75a01",
            run_directory=Path("/state/runs/20261009T120000Z-b75a01"),
            procedure=Procedure(
                name="deliver",
                location="built-in",
                argument="deliver",
                capabilities=("read", "write"),
                body="Deliver the task.",
            ),
            slot="build",
            role=ResolvedRole(
                slot="build",
                role="builder",
                source="built-in",
                front_matter={"reasoning": "standard"},
                body="You build.",
            ),
            client="double-client",
            client_adapter=object(),
            document=object(),
            progress_file=Path("/state/runs/20261009T120000Z-b75a01/progress.awawa"),
            configuration=Configuration(),
            project=None,
            cwd=Path("/project"),
            worktree=Path("/project"),
            disposable_worktree=False,
            capabilities=("read", "write"),
            wall_limit_s=1500.0,
            budget=CAP_OF_FORTY_STEPS,
            arguments=NO_ARGUMENTS,
            wave=NO_WAVE,
            task=NO_TASK,
            brief_path=None,
            brief=NO_BRIEF,
            counts_steps=True,
            reads_actions=False,
            reads_transcripts=False,
            handovers=NO_HANDOVER,
            warnings=NO_WARNINGS,
            forge_environment={"GH_TOKEN": "token-of-octo-builder"},
        )

        # Act
        representation = repr(plan)

        # Assert
        self.assertNotIn("token-of-octo-builder", representation)


RUN_ID = "20261019T090000Z-c0ffee"


class PlanRunTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.project = self.root / "project"
        self.project.mkdir()
        self.brief = self.root / "brief.md"
        self.brief.write_text("Start from the base.\n")

    def create_request(self, **changes) -> RunRequest:
        return RunRequest(
            **{
                "procedure": "build-task",
                "slot": "build",
                "project": None,
                "cwd": str(self.project),
                "brief": None,
                "arguments": (),
                "run_id": None,
                "wave": None,
                "task": None,
                **changes,
            }
        )

    def plan(self, request: RunRequest, settings: dict, project: Entity | None = None, run_process=None):
        configuration = Configuration(client="fake", clients={"fake": settings}, seconds_per_step=20)
        runtime = create_test_runtime(self.paths, **({} if run_process is None else {"run_process": run_process}))
        return plan_run(
            request,
            RunSetting(configuration, project, "fake"),
            RunPlugins(client_adapter=fake, document=markdown),
            runtime,
        )


class PlanRunOfAWritingProcedureTest(PlanRunTestCase):
    def test_should_plan_the_run_in_its_directory_from_the_procedure_the_role_and_the_probe(self):
        # Arrange
        request = self.create_request(
            brief=str(self.brief), arguments=("task=@TASK.B1",), run_id=RUN_ID, wave="w1", task="B1"
        )

        # Act
        plan = self.plan(request, {"features": "step_count"})

        # Assert
        self.assertEqual(plan.run_directory, self.paths.state_root / "runs" / RUN_ID)
        self.assertEqual(plan.procedure.name, "build-task")
        self.assertEqual(plan.role.role, "builder")
        self.assertEqual(plan.capabilities, ("read", "write", "shell"))
        self.assertEqual(plan.arguments, {"task": "@TASK.B1"})
        self.assertEqual(plan.brief, "Start from the base.\n")
        self.assertEqual(plan.worktree, self.project)
        self.assertEqual(plan.disposable_worktree, False)
        self.assertEqual(plan.warnings, ())
        self.assertEqual(plan.handovers, 2)
        self.assertEqual(plan.first_segment, 1)
        self.assertEqual(plan.resumed_session, None)

    def test_should_hold_the_capabilities_of_the_procedure_to_those_the_role_of_its_slot_allows(self):
        # Arrange
        rows = [
            ("explore", "explorer", ("read", "shell")),
            ("review", "reviewer", ("read", "shell")),
            ("remediate", "remediator", ("read", "write", "shell")),
        ]
        for slot, role, capabilities in rows:
            with self.subTest(slot=slot):
                # Act
                plan = self.plan(self.create_request(slot=slot), {"features": "step_count"})

                # Assert
                self.assertEqual(plan.role.role, role)
                self.assertEqual(plan.capabilities, capabilities)

    def test_should_hold_the_edit_tools_the_probe_names(self):
        # Act
        plan = self.plan(self.create_request(), {"features": "step_count", "edit_tools": "Edit, Write"})

        # Assert
        self.assertEqual(plan.edit_tools, ("Edit", "Write"))

    def test_should_name_a_new_run_by_its_instant(self):
        # Act
        plan = self.plan(self.create_request(), {"features": "step_count"})

        # Assert
        self.assertRegex(plan.run_id, r"^20261019T090000Z-[0-9a-f]{6}$")


class PlanRunOfAProcedureOnTheSlotOfARoleHoldingFewerCapabilitiesTest(PlanRunTestCase):
    def test_should_grant_the_capabilities_the_procedure_and_the_role_both_hold(self):
        # Arrange
        request = self.create_request(procedure="build-task", slot="review")

        # Act
        plan = self.plan(request, {"features": "step_count"})

        # Assert
        self.assertEqual(plan.capabilities, ("read", "shell"))


class PlanRunOfASlotTheSlotClientsTableBindsTest(PlanRunTestCase):
    def test_should_name_the_client_of_the_slot_over_the_client_key(self):
        # Arrange
        configuration = Configuration(
            client="claude-code", clients={"codex": {"features": "step_count"}}, slot_clients={"build": "codex"}
        )
        no_project = None
        setting = RunSetting(configuration, no_project, "codex")

        # Act
        plan = plan_run(
            self.create_request(),
            setting,
            RunPlugins(client_adapter=fake, document=markdown),
            create_test_runtime(self.paths),
        )

        # Assert
        self.assertEqual(plan.client, "codex")


class PlanRunOfAReadingProcedureTest(PlanRunTestCase):
    def test_should_hold_the_budget_on_the_clock_in_a_disposable_worktree(self):
        # Arrange
        procedure = self.root / "survey.md"
        procedure.write_text("---\ncapabilities: read\nbudget: 10\n---\nSurvey the code.\n")

        # Act
        plan = self.plan(self.create_request(procedure=str(procedure), run_id=RUN_ID), {})

        # Assert
        self.assertEqual(plan.worktree, self.paths.state_root / "runs" / RUN_ID / "worktree")
        self.assertEqual(plan.disposable_worktree, True)
        self.assertEqual(plan.counts_steps, False)
        self.assertEqual(
            plan.warnings,
            (
                (
                    "fake counts no steps: the budget of 75 steps is held on the clock"
                    " and the run cut at its limit of 1880 s"
                ),
            ),
        )


class PlanRunOfARoleWithNoMeasuredSegmentTest(PlanRunTestCase):
    def test_should_apply_the_budget_the_role_ships_and_hold_the_wall_limit_to_it(self):
        # Act
        plan = self.plan(self.create_request(), {"features": "step_count"})

        # Assert
        self.assertEqual(
            plan.budget,
            RoleBudget(shipped=75, computed=None, applied=75, segments=0, restarts=0, growth=None, restart_tokens=None),
        )
        self.assertEqual(plan.wall_limit_s, 1880)

    def test_should_record_no_change_of_the_applied_cap(self):
        # Act
        plan = self.plan(self.create_request(), {"features": "step_count"})

        # Assert
        self.assertIsNone(plan.budget_applied)


class PlanRunOfARoleMeasuredAtTheDigestsOfTheLaunchTestCase(PlanRunTestCase):
    def setUp(self):
        super().setUp()
        (self.paths.config_root / "roles").mkdir(parents=True)
        (self.paths.config_root / "roles" / "mason.md").write_text(MASON_ROLE)
        self.survey = self.root / "survey.md"
        self.survey.write_text(SURVEY_PROCEDURE)
        self.ledger = self.paths.state_root / "ledger" / "2026-10.jsonl"
        self.ledger.parent.mkdir(parents=True)
        self.ledger.write_text(MASON_SEGMENTS)


class PlanRunOfARoleMeasuredAtTheDigestsOfTheLaunchTest(PlanRunOfARoleMeasuredAtTheDigestsOfTheLaunchTestCase):
    def test_should_apply_the_cap_computed_from_the_segments_of_the_role(self):
        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey)), {"features": "step_count"})

        # Assert
        self.assertEqual(
            plan.budget,
            RoleBudget(
                shipped=40, computed=63, applied=63, segments=6, restarts=3, growth=100.0, restart_tokens=200000.0
            ),
        )
        self.assertEqual(plan.wall_limit_s, 1580)

    def test_should_measure_no_segment_once_the_procedure_changed(self):
        # Arrange
        self.survey.write_text("---\ncapabilities: read\n---\nSurvey the code and the tests.\n")

        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey)), {"features": "step_count"})

        # Assert
        self.assertEqual(plan.budget.applied, 40)

    def test_should_record_the_change_from_the_shipped_budget_to_the_computed_cap(self):
        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey)), {"features": "step_count"})

        # Assert
        self.assertEqual(
            plan.budget_applied,
            BudgetApplied(
                role="mason", before=40, after=63, segments=6, restarts=3, growth=100.0, restart_tokens=200000.0
            ),
        )


class PlanRunOfARoleSharingItsPackageWithAMeasuredRoleTest(PlanRunOfARoleMeasuredAtTheDigestsOfTheLaunchTestCase):
    def test_should_measure_none_of_the_segments_of_the_other_role(self):
        # Arrange
        (self.paths.config_root / "roles" / "stonemason.md").write_text(STONEMASON_ROLE)

        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey), slot="plan"), {"features": "step_count"})

        # Assert
        self.assertEqual(plan.budget.segments, 0)


class PlanRunOfARoleWhoseCapWasAppliedBeforeTest(PlanRunOfARoleMeasuredAtTheDigestsOfTheLaunchTestCase):
    def test_should_record_no_change_when_the_cap_is_the_one_last_applied(self):
        # Arrange
        self.ledger.write_text(MASON_SEGMENTS + MASON_BUDGET_APPLIED)

        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey)), {"features": "step_count"})

        # Assert
        self.assertIsNone(plan.budget_applied)

    def test_should_compare_the_cap_with_the_latest_one_applied(self):
        # Arrange
        self.ledger.write_text(EARLIER_MASON_BUDGET_APPLIED + MASON_SEGMENTS + MASON_BUDGET_APPLIED)

        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey)), {"features": "step_count"})

        # Assert
        self.assertIsNone(plan.budget_applied)

    def test_should_compare_the_cap_with_none_applied_to_another_role(self):
        # Arrange
        self.ledger.write_text(MASON_SEGMENTS + STONEMASON_BUDGET_APPLIED)

        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey)), {"features": "step_count"})

        # Assert
        self.assertEqual(plan.budget_applied.before, 40)

    def test_should_record_the_return_to_the_shipped_budget_once_the_procedure_changed(self):
        # Arrange
        self.ledger.write_text(MASON_SEGMENTS + MASON_BUDGET_APPLIED)
        self.survey.write_text("---\ncapabilities: read\n---\nSurvey the code and the tests.\n")

        # Act
        plan = self.plan(self.create_request(procedure=str(self.survey)), {"features": "step_count"})

        # Assert
        self.assertEqual(
            plan.budget_applied,
            BudgetApplied(role="mason", before=63, after=40, segments=0, restarts=0, growth=None, restart_tokens=None),
        )


class PlanRunOfAResumedRunTest(PlanRunTestCase):
    def test_should_resume_after_its_last_segment_on_the_session_it_left(self):
        # Arrange
        write_run_result(
            self.paths.state_root / "runs" / RUN_ID / "segments" / "1" / "result.json", "handed_over", session="s1"
        )

        # Act
        plan = self.plan(self.create_request(run_id=RUN_ID, resume=True), {"operations": "resume"})

        # Assert
        self.assertEqual(plan.resumed, True)
        self.assertEqual(plan.first_segment, 2)
        self.assertEqual(plan.resumed_session, "s1")

    def test_should_resume_after_its_last_segment_in_a_session_of_its_own_when_the_client_cannot_resume(self):
        # Arrange
        write_run_result(
            self.paths.state_root / "runs" / RUN_ID / "segments" / "1" / "result.json", "failed", session="s1"
        )
        client_without_operations = {}

        # Act
        plan = self.plan(self.create_request(run_id=RUN_ID, resume=True), client_without_operations)

        # Assert
        self.assertEqual(plan.first_segment, 2)
        self.assertIsNone(plan.resumed_session)


class PlanRunOfARegisteredProjectTest(PlanRunTestCase):
    def create_policies(self) -> RecordingProcessRunner:
        return RecordingProcessRunner(
            {
                ("awawa", "status", "POLICY", "--json", str(self.paths.config_root)): ProcessAnswer(
                    stdout=json.dumps({"entities": []})
                )
            }
        )

    def test_should_run_in_the_project_with_the_role_it_binds(self):
        # Arrange
        project = Entity(
            name="shop",
            fields=(
                EntityField(name="PATH", value=str(self.project)),
                EntityField(name="ROLE", value="build = builder"),
            ),
        )

        # Act
        plan = self.plan(self.create_request(project="shop", cwd=None), {}, project, self.create_policies())

        # Assert
        self.assertEqual(plan.cwd, self.project)
        self.assertEqual(plan.role.role, "builder")
        self.assertEqual(plan.project, "shop")

    def test_should_refuse_a_role_binding_off_the_slot_name_form(self):
        # Arrange
        project = Entity(name="shop", fields=(EntityField(name="ROLE", value="build"),))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.plan(self.create_request(project="shop"), {}, project, self.create_policies())

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.shop has ROLE build, not slot=name")


class PlanRunOfNoProjectAndNoDirectoryTest(PlanRunTestCase):
    def test_should_run_in_the_current_directory(self):
        # Act
        plan = self.plan(self.create_request(cwd=None), {})

        # Assert
        self.assertEqual(plan.cwd, Path.cwd())


class PlanRunRefusalTest(PlanRunTestCase):
    def test_should_refuse_a_request_it_cannot_plan(self):
        for changes, refusal_type, message in [
            ({"run_id": "bad"}, UsageError, "bad is not a run id"),
            ({"arguments": ("task",)}, BrigadeError, "the argument task is not key=value"),
            ({"arguments": ("=B1",)}, BrigadeError, "the argument =B1 is not key=value"),
        ]:
            with self.subTest(changes=changes):
                # Act
                with self.assertRaises(refusal_type) as refusal:
                    self.plan(self.create_request(**changes), {})

                # Assert
                self.assertEqual(str(refusal.exception), message)

    def test_should_refuse_a_directory_or_a_brief_that_does_not_exist(self):
        for changes, message in [
            ({"cwd": str(self.root / "missing")}, f"no directory {self.root / 'missing'}"),
            ({"brief": str(self.root / "missing.md")}, f"no brief file {self.root / 'missing.md'}"),
        ]:
            with self.subTest(changes=changes):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    self.plan(self.create_request(**changes), {})

                # Assert
                self.assertEqual(str(refusal.exception), message)
