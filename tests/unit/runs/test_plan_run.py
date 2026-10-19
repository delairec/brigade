import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.documents import markdown
from brigade.adapters.test_clients import fake
from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError, UsageError
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.plan_run import RunPlan, RunRequest, plan_run
from brigade.runs.read_run_setting import RunSetting
from brigade.runs.resolve_procedure import Procedure
from brigade.system.read_configuration import Configuration
from tests.unit.create_test_runtime import create_test_paths, create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.runs.run_directory_writer import write_run_result

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
                budget=40,
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
        return plan_run(request, RunSetting(configuration, project, "fake"), fake, markdown, runtime)


class PlanRunOfAWritingProcedureTest(PlanRunTestCase):
    def test_should_plan_the_run_in_its_directory_from_the_procedure_the_role_and_the_probe(self):
        # Arrange
        request = self.create_request(
            brief=str(self.brief), arguments=("task=@TASK.B1",), run_id=RUN_ID, wave="w1", task="B1"
        )

        # Act
        plan = self.plan(request, {"features": "step_count"})

        # Assert
        self.assertEqual(
            (
                plan.run_directory,
                plan.procedure.name,
                plan.role.role,
                plan.capabilities,
                plan.arguments,
                plan.brief,
                plan.worktree,
                plan.disposable_worktree,
                plan.warnings,
                plan.handovers,
                plan.first_segment,
                plan.resumed_session,
            ),
            (
                self.paths.state_root / "runs" / RUN_ID,
                "build-task",
                "builder",
                ("read", "write", "shell"),
                {"task": "@TASK.B1"},
                "Start from the base.\n",
                self.project,
                False,
                (),
                2,
                1,
                None,
            ),
        )

    def test_should_name_a_new_run_by_its_instant(self):
        # Act
        plan = self.plan(self.create_request(), {"features": "step_count"})

        # Assert
        self.assertRegex(plan.run_id, r"^20261019T090000Z-[0-9a-f]{6}$")


class PlanRunOfAReadingProcedureTest(PlanRunTestCase):
    def test_should_hold_the_budget_on_the_clock_in_a_disposable_worktree(self):
        # Arrange
        procedure = self.root / "survey.md"
        procedure.write_text("---\ncapabilities: read\nbudget: 10\n---\nSurvey the code.\n")

        # Act
        plan = self.plan(self.create_request(procedure=str(procedure), run_id=RUN_ID), {})

        # Assert
        self.assertEqual(
            (plan.worktree, plan.disposable_worktree, plan.counts_steps, plan.warnings),
            (
                self.paths.state_root / "runs" / RUN_ID / "worktree",
                True,
                False,
                (
                    (
                        "fake counts no steps: the budget of 10 steps is held on the clock"
                        " and the run cut at its limit of 260 s"
                    ),
                ),
            ),
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
        self.assertEqual((plan.resumed, plan.first_segment, plan.resumed_session), (True, 2, "s1"))


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
        self.assertEqual((plan.cwd, plan.role.role, plan.project), (self.project, "builder", "shop"))

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
