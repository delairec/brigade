import json
import shutil
import unittest
from pathlib import Path

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, TURN_LIMIT_RESULT, RunTestCase
from tests.cli.temporary_instructions import TemporaryInstructions
from tests.cli.temporary_machine import REPOSITORY_ROOT
from tests.cli.temporary_project import TemporaryProject

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"
INSTANT_PATTERN = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"
BUILT_IN_BUILDER = REPOSITORY_ROOT / "brigade" / "roles" / "data" / "builder.md"
NOT_IN_A_WAVE = "not launched by a wave"
CUT = "cut at the wall-time limit"
QUICK_PROCEDURE = "---\ncapabilities: read, write, shell\nbudget: 1\n---\nAnswer at once.\n"
MACHINE_BUILDER = (
    "---\n"
    "name: {name}\n"
    "slot: {slot}\n"
    "work: builds on this machine\n"
    "reasoning: light\n"
    "capabilities: read, write, shell\n"
    "budget: 20\n"
    "returns: the branch\n"
    "---\n"
    "You build on this machine.\n"
)


class BrigadeRunOfAProcedureGivenByPath(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        self.brief = self.workspace / "brief.md"
        self.brief.write_text("Deliver B06.\n")

    def run_deliver(self, *options: str):
        return self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--brief", str(self.brief),
            "task=B06", *options,
        )

    def test_should_print_the_run_as_a_document(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertRegex(document["run"], RUN_ID_PATTERN)
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "run": document["run"],
                "procedure": "deliver",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": None,
                "segments": 1,
                "outcome": "done",
            },
        )

    def test_should_print_the_run_as_text(self):
        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(completed.stdout, r"^run \d{8}T\d{6}Z-[0-9a-f]{6}: deliver as builder \(build\) done after 1 segment\n$")

    def test_should_record_the_finished_run_in_the_ledger(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertRegex(finished.pop("ts"), INSTANT_PATTERN)
        self.assertEqual(
            finished,
            {
                "schema_version": 1,
                "event": "run.finished",
                "run": json.loads(completed.stdout)["run"],
                "segment": 1,
                "procedure": "deliver",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": None,
                "session": "fake-session",
                "steps": 12,
                "duration_ms": 61000,
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 3400,
                    "cache_creation_input_tokens": 16778,
                    "cache_read_input_tokens": 98000,
                },
                "outcome": "done",
                "error_class": None,
                "exit": 0,
                "wave": None,
                "task": None,
                "nulls": {
                    "project": "no project given",
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "error_class": "the run did not fail",
                },
            },
        )

    def test_should_keep_the_brief_the_role_the_output_the_progress_and_the_result_in_the_run_directory(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual(
            sorted(path.relative_to(run_directory).as_posix() for path in run_directory.rglob("*") if path.is_file()),
            [
                "pid",
                "progress.md",
                "result.json",
                "role.md",
                "run.json",
                "segments/1/brief.md",
                "segments/1/stderr.log",
                "segments/1/stdout.log",
            ],
        )

    def test_should_send_the_procedure_the_arguments_the_brief_and_the_progress_file_to_the_client(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual(
            (run_directory / "segments" / "1" / "brief.md").read_text(),
            "# Procedure deliver\n\n"
            "Deliver the task the brief names.\n\n"
            "# Arguments\n\n"
            "task=B06\n\n"
            "# Brief\n\n"
            "Deliver B06.\n\n"
            "# Progress file\n\n"
            f"{run_directory / 'progress.md'}\n",
        )

    def test_should_keep_the_package_of_the_resolved_role(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual((run_directory / "role.md").read_text(), BUILT_IN_BUILDER.read_text())

    def test_should_keep_the_normalised_result(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual(json.loads((run_directory / "result.json").read_text()), DONE_RESULT)


class BrigadeRunOfAProcedureGivenByName(RunTestCase):
    def setUp(self):
        super().setUp()
        self.instructions = Path(self.root.name) / "instructions"
        (self.instructions / "procedures").mkdir(parents=True)
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{self.instructions}"\n')
        self.record("builder", DONE_RESULT)

    def test_should_resolve_it_in_the_procedures_of_the_instructions_corpus(self):
        # Arrange
        (self.instructions / "procedures" / "review.md").write_text(PROCEDURE_OF_THE_CORPUS)

        # Act
        completed = self.run_brigade("run", "review", "--slot", "build", "--cwd", str(self.workspace), "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["procedure"], "review")

    def test_should_exit_1_naming_a_procedure_that_resolves_nowhere(self):
        # Act
        completed = self.run_brigade("run", "missing", "--slot", "build", "--cwd", str(self.workspace))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade run: no procedure missing: not shipped with brigade and not in {self.instructions}/procedures\n",
        )


PROCEDURE_OF_THE_CORPUS = "---\ncapabilities: read\nbudget: 30\n---\nReview the pull request.\n"


class BrigadeRunOfAProcedureOffItsDeclaration(RunTestCase):
    def test_should_exit_1_naming_the_procedure_and_what_it_lacks(self):
        rows = [
            ("no budget", "---\ncapabilities: read\n---\nBody.\n", "lacks budget in its front matter"),
            ("no capabilities", "---\nbudget: 10\n---\nBody.\n", "lacks capabilities in its front matter"),
            ("no front matter", "Body.\n", "has no front matter between two --- lines"),
        ]
        self.configure_fake(COUNTING_CLIENT)
        for case, content, problem in rows:
            with self.subTest(case=case):
                # Arrange
                self.procedure.write_text(content)

                # Act
                completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, f"brigade run: the procedure {self.procedure} {problem}\n")


class BrigadeRunOfASlotWhoseRoleAllowsLessThanTheProcedure(RunTestCase):
    def test_should_record_the_capabilities_the_procedure_declares_that_the_role_allows(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("explorer", DONE_RESULT)

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "explore", "--cwd", str(self.workspace), "task=B06", "--json"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = json.loads(completed.stdout)["run"]
        self.assertEqual(
            self.read_run_record(run_id),
            {
                "schema_version": 1,
                "run": run_id,
                "procedure": "deliver",
                "procedure_path": str(self.procedure),
                "slot": "explore",
                "role": "explorer",
                "role_source": "built-in",
                "client": "fake",
                "project": None,
                "cwd": str(self.workspace),
                "worktree": str(self.workspace),
                "capabilities": ["read", "shell"],
                "budget": 75,
                "wall_limit_s": 2820,
                "arguments": {"task": "B06"},
            },
        )


class BrigadeRunDetached(RunTestCase):
    def test_should_print_the_run_id_and_exit_0_while_the_run_finishes_in_the_background(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--detach")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = completed.stdout.strip()
        self.assertRegex(run_id, RUN_ID_PATTERN)
        self.assertRegex((self.runs / run_id / "pid").read_text(), r"^\d+\n$")
        self.wait_for_file(self.runs / run_id / "result.json")
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["run"], run_id)


class BrigadeRunHandOver(RunTestCase):
    def setUp(self):
        super().setUp()
        self.record("builder", TURN_LIMIT_RESULT)

    def run_deliver(self):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json")

    def test_should_relaunch_a_segment_ended_on_the_step_cap_with_progress_up_to_two_hand_overs(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "run": document["run"],
                "procedure": "deliver",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": None,
                "segments": 3,
                "outcome": "failed",
            },
        )

    def test_should_write_one_finished_event_per_segment(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(len(self.read_events("run.finished")), 3)

    def test_should_give_the_progress_file_as_the_first_context_of_the_next_segment(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual(
            (run_directory / "segments" / "2" / "brief.md").read_text(),
            "# Progress so far\n\n"
            "step 1 done\n\n"
            "# Procedure deliver\n\n"
            "Deliver the task the brief names.\n\n"
            "# Progress file\n\n"
            f"{run_directory / 'progress.md'}\n",
        )

    def test_should_not_relaunch_a_segment_ended_on_the_step_cap_with_an_empty_progress_file(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 1)

    def test_should_record_a_signal_naming_the_procedure_the_run_and_the_budget(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        [signal] = self.read_events("signal.recorded")
        self.assertRegex(signal.pop("ts"), INSTANT_PATTERN)
        self.assertEqual(
            signal,
            {
                "schema_version": 1,
                "event": "signal.recorded",
                "signal": "budget_reached",
                "project": None,
                "procedure": "deliver",
                "run": json.loads(completed.stdout)["run"],
                "segment": 1,
                "budget": 75,
            },
        )


class BrigadeRunOnTheClock(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + 'delay = "10"\n', keys="seconds_per_step = 0.2\n")
        self.record("builder", DONE_RESULT)
        self.quick = self.procedure.with_name("quick.md")
        self.quick.write_text(QUICK_PROCEDURE)

    def run_quick(self):
        return self.run_brigade("run", str(self.quick), "--slot", "build", "--cwd", str(self.workspace), "--json")

    def test_should_cut_the_client_at_its_wall_time_limit(self):
        # Act
        completed = self.run_quick()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertRegex(finished.pop("ts"), INSTANT_PATTERN)
        self.assertLess(finished.pop("duration_ms"), 10000)
        self.assertEqual(
            finished,
            {
                "schema_version": 1,
                "event": "run.finished",
                "run": json.loads(completed.stdout)["run"],
                "segment": 1,
                "procedure": "quick",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": None,
                "session": None,
                "steps": None,
                "usage": None,
                "outcome": "wall_limit",
                "error_class": None,
                "exit": None,
                "wave": None,
                "task": None,
                "nulls": {
                    "project": "no project given",
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "session": CUT,
                    "steps": CUT,
                    "usage": CUT,
                    "error_class": CUT,
                    "exit": CUT,
                },
            },
        )

    def test_should_record_a_signal_when_the_clock_cuts_the_run(self):
        # Act
        completed = self.run_quick()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        [signal] = self.read_events("signal.recorded")
        self.assertEqual(signal["budget"], 1)


class BrigadeRunWithAClientThatCountsNoSteps(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake('features = "tool_grants"\n')
        self.record("builder", DONE_RESULT)

    def test_should_warn_that_the_budget_is_held_on_the_clock(self):
        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stderr,
            "brigade run: fake counts no steps: the budget of 75 steps is held on the clock"
            " and the run cut at its limit of 2820 s\n",
        )

    def test_should_record_null_steps_with_their_reason(self):
        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["nulls"]["steps"], "the client counts no steps")


class BrigadeRunWithAClientThatGrantsNoTools(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake('features = "step_count"\n')
        self.project = TemporaryProject(self.workspace / "shop", self.machine.describe_environment())
        self.project.run_git("commit", "--quiet", "--allow-empty", "-m", "initial")

    def run_slot(self, slot: str):
        return self.run_brigade("run", str(self.procedure), "--slot", slot, "--cwd", str(self.project.path), "--json")

    def test_should_run_a_reading_slot_in_a_disposable_worktree_removed_after_it(self):
        # Arrange
        self.record("explorer", DONE_RESULT)

        # Act
        completed = self.run_slot("explore")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = json.loads(completed.stdout)["run"]
        disposable_worktree = self.runs / run_id / "worktree"
        self.assertEqual(self.read_run_record(run_id)["worktree"], str(disposable_worktree))
        self.assertFalse(disposable_worktree.exists())
        self.assertEqual(self.project.run_git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_should_run_a_writing_slot_in_the_directory_it_is_given(self):
        # Arrange
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_run_record(json.loads(completed.stdout)["run"])["worktree"], str(self.project.path))


@unittest.skipUnless(shutil.which("awawa"), "awawa is not on PATH")
class BrigadeRunOfAProject(RunTestCase):
    def setUp(self):
        super().setUp()
        initialised = self.machine.run_init()
        self.assertEqual(initialised.returncode, 0, initialised.stderr)
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

    def register(self, *fields: str) -> None:
        lines = "".join(f"\t{field}\n" for field in fields)
        (self.machine.corpus / "projects.awawa").write_text(
            f'PROJECT shop\n\tPATH "{self.workspace}"\n\tMAIN "main"\n{lines}\tSTATUS active\n'
        )

    def run_slot(self, slot: str = "build"):
        return self.run_brigade("run", str(self.procedure), "--slot", slot, "--project", "shop", "--json")

    def test_should_record_the_project_of_the_run(self):
        # Arrange
        self.register()

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["project"], "shop")

    def test_should_run_in_the_path_of_the_project_when_no_directory_is_given(self):
        # Arrange
        self.register()

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_run_record(json.loads(completed.stdout)["run"])["cwd"], str(self.workspace))

    def test_should_run_with_the_client_the_project_names(self):
        # Arrange
        self.machine.write_configuration(
            f'client = "claude-code"\n[clients.fake]\nrecordings = "{self.recordings}"\n{COUNTING_CLIENT}'
        )
        self.register('CLIENT "fake"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["client"], "fake")

    def test_should_bind_the_slot_to_the_role_the_project_names(self):
        # Arrange
        self.register('ROLE "build=verifier"')
        self.record("verifier", DONE_RESULT)

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role"], "verifier")

    def test_should_exit_1_naming_a_project_role_found_nowhere(self):
        # Arrange
        self.register('ROLE "build=nobody"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade run: @PROJECT.shop binds build to nobody, a role found nowhere\n")

    def test_should_resolve_the_built_in_role_of_a_builtin_roleset_over_a_machine_role(self):
        # Arrange
        self.write_role_file(self.machine.corpus / "roles", "mybuilder", "build")
        self.register('ROLESET "builtin"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role"], "builder")

    def test_should_resolve_the_role_file_of_a_roleset_directory(self):
        # Arrange
        roleset = Path(self.root.name) / "shop-roles"
        self.write_role_file(roleset, "shopbuilder", "build")
        self.record("shopbuilder", DONE_RESULT)
        self.register(f'ROLESET "{roleset}"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role"], "shopbuilder")

    def test_should_resolve_the_agent_entity_the_slot_table_binds_for_a_corpus_roleset(self):
        # Arrange
        instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        self.configure_fake(
            COUNTING_CLIENT + '\n[slots]\nplan = "planner"\n', keys=f'instructions = "{instructions.root}"\n'
        )
        self.write_role_file(self.machine.corpus / "roles", "localplanner", "plan")
        self.record("planner", DONE_RESULT)
        self.register('ROLESET "corpus"')

        # Act
        completed = self.run_slot("plan")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role"], "planner")

    def test_should_hand_over_up_to_the_handovers_of_the_project_policy(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", TURN_LIMIT_RESULT)
        self.register()
        (self.machine.corpus / "policies.awawa").write_text("POLICY shop_policy\n\tPROJECT @PROJECT.shop\n\tHANDOVERS 1\n")

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 2)

    def write_role_file(self, directory: Path, name: str, slot: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.md").write_text(MACHINE_BUILDER.format(name=name, slot=slot))
