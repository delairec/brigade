import json
import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, TURN_LIMIT_RESULT, RunTestCase
from tests.cli.temporary_instructions import TemporaryInstructions
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, REPOSITORY_ROOT
from tests.cli.temporary_project import TemporaryProject

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"
INSTANT_PATTERN = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"
BUILT_IN_BUILDER = REPOSITORY_ROOT / "brigade" / "roles" / "data" / "builder.md"
RECORDING_CLAUDE = Path(__file__).resolve().parent / "fixtures" / "executables" / "claude-recording"
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


class BrigadeRunOfAProcedureGivenByPathTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        self.brief = self.workspace / "brief.md"
        self.brief.write_text("Deliver B06.\n")

    def run_deliver(self, *options: str):
        return self.run_brigade(
            "run",
            str(self.procedure),
            "--slot",
            "build",
            "--cwd",
            str(self.workspace),
            "--brief",
            str(self.brief),
            "task=B06",
            *options,
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
        self.assertRegex(
            completed.stdout, r"^run \d{8}T\d{6}Z-[0-9a-f]{6}: deliver as builder \(build\) done after 1 segment\n$"
        )

    def test_should_record_the_finished_run_in_the_ledger(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertRegex(finished.pop("ts"), INSTANT_PATTERN)
        self.assertLess(finished.pop("duration_ms"), 10000)
        self.assertEqual(
            finished,
            {
                "schema_version": 2,
                "event": "run.finished",
                "run": json.loads(completed.stdout)["run"],
                "segment": 1,
                "procedure": "deliver",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": None,
                "session": "fake-session",
                "main_steps": 12,
                "total_steps": None,
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
                    "total_steps": "the client reads no transcript",
                    "error_class": "the run did not fail",
                },
                "cost_usd": 0.42,
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
                "journal.jsonl",
                "pid",
                "processes.jsonl",
                "progress.md",
                "result.json",
                "role.md",
                "run.json",
                "segments/1/brief.md",
                "segments/1/result.json",
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
        self.assertEqual(
            json.loads((run_directory / "result.json").read_text()),
            {
                "schema_version": 1,
                "outcome": "done",
                "steps": 12,
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 3400,
                    "cache_creation_input_tokens": 16778,
                    "cache_read_input_tokens": 98000,
                },
                "session_id": "fake-session",
                "duration_ms": 61000,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )


class BrigadeRunOfAClientReadingTranscriptsTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(f'{COUNTING_CLIENT}operations = "transcripts"\n')
        self.record("builder", DONE_RESULT)
        transcripts = {
            "schema_version": 1,
            "messages": [
                {"role": "user", "timestamp": None, "content": "Deliver B83.", "tool_calls": 0},
                {"role": "assistant", "timestamp": None, "content": [], "tool_calls": 2},
            ],
            "subagents": [
                {"messages": [{"role": "assistant", "timestamp": None, "content": [], "tool_calls": 1}]},
            ],
        }
        (self.recordings / "fake-session.transcripts.json").write_text(json.dumps(transcripts))

    def test_should_record_the_steps_of_the_main_session_and_of_the_session_with_its_sub_agent(self):
        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["main_steps"], 3)
        self.assertEqual(finished["total_steps"], 5)


class BrigadeRunOnClaudeCodeTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration('client = "claude-code"\n')
        self.brief = self.workspace / "brief.md"
        self.brief.write_text("Deliver B71.\n")

    def test_should_hand_the_client_the_role_file_and_grant_it_the_progress_file(self):
        # Arrange
        environment = {
            **self.machine.describe_environment(),
            "PATH": os.pathsep.join([str(RECORDING_CLAUDE), os.environ["PATH"]]),
        }

        # Act
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "run",
            str(self.procedure),
            "--slot",
            "build",
            "--cwd",
            str(self.workspace),
            "--brief",
            str(self.brief),
            "--json",
            environment=environment,
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual(
            (run_directory / "progress.md").read_text().splitlines(),
            [
                "--print",
                "--output-format",
                "stream-json",
                "--verbose",
                "--permission-mode",
                "dontAsk",
                "--model",
                "opus",
                "--effort",
                "high",
                "--max-turns",
                "94",
                "--append-system-prompt-file",
                f"{run_directory / 'role.md'}",
                "--allowedTools",
                (
                    f"Read,Glob,Grep,Edit,Write,NotebookEdit,Bash,Write(/{run_directory / 'progress.md'}),"
                    f"Edit(/{run_directory / 'progress.md'})"
                ),
            ],
        )


class BrigadeRunOfAProcedureGivenByNameTest(RunTestCase):
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


class BrigadeRunOfAProcedureOffItsDeclarationTest(RunTestCase):
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
                completed = self.run_brigade(
                    "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace)
                )

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, f"brigade run: the procedure {self.procedure} {problem}\n")


class BrigadeRunOfARequestItCannotPlanTest(RunTestCase):
    def test_should_exit_1_naming_what_it_cannot_plan_from(self):
        missing = self.workspace / "missing"
        rows = [
            ("a directory that does not exist", ["--cwd", str(missing)], f"no directory {missing}"),
            (
                "a brief that does not exist",
                ["--cwd", str(self.workspace), "--brief", str(missing)],
                f"no brief file {missing}",
            ),
            ("an argument with no key", ["--cwd", str(self.workspace), "=B06"], "the argument =B06 is not key=value"),
        ]
        self.configure_fake(COUNTING_CLIENT)
        for case, options, refusal in rows:
            with self.subTest(case=case):
                # Act
                completed = self.run_brigade("run", str(self.procedure), "--slot", "build", *options)

                # Assert
                self.assertEqual((completed.returncode, completed.stderr), (1, f"brigade run: {refusal}\n"))

    def test_should_exit_2_for_a_run_id_off_its_pattern(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--run-id", "latest"
        )

        # Assert
        self.assertEqual((completed.returncode, completed.stderr), (2, "brigade run: latest is not a run id\n"))

    def test_should_exit_1_when_config_toml_names_no_client(self):
        # Arrange
        configuration = self.machine.write_configuration("")

        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, f"brigade run: config.toml names no client: set the client key in {configuration}\n"),
        )


class BrigadeRunWithNoDirectoryGivenTest(RunTestCase):
    def test_should_run_in_the_current_directory(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_run_record(json.loads(completed.stdout)["run"])["worktree"], os.getcwd())


class BrigadeRunOfASlotWhoseRoleAllowsLessThanTheProcedureTest(RunTestCase):
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


class BrigadeRunDetachedTest(RunTestCase):
    def test_should_print_the_run_id_and_exit_0_while_the_run_finishes_in_the_background(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--detach"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = completed.stdout.strip()
        self.assertRegex(run_id, RUN_ID_PATTERN)
        self.assertRegex((self.runs / run_id / "pid").read_text(), r"^\d+\n$")
        self.wait_for_file(self.runs / run_id / "result.json")
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["run"], run_id)


class BrigadeRunHandOverTest(RunTestCase):
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


class BrigadeRunOnTheClockTest(RunTestCase):
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
                "schema_version": 2,
                "event": "run.finished",
                "run": json.loads(completed.stdout)["run"],
                "segment": 1,
                "procedure": "quick",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": None,
                "session": None,
                "main_steps": None,
                "total_steps": None,
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
                    "main_steps": CUT,
                    "total_steps": CUT,
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


class BrigadeRunWithAClientThatCountsNoStepsTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake('features = "tool_grants"\n')
        self.record("builder", DONE_RESULT)

    def test_should_warn_that_the_budget_is_held_on_the_clock(self):
        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stderr,
            "brigade run: fake counts no steps: the budget of 75 steps is held on the clock"
            " and the run cut at its limit of 2820 s\n",
        )

    def test_should_record_null_steps_with_their_reason(self):
        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(
            finished["nulls"]["main_steps"], "the client counts no steps and the client reads no transcript"
        )


class BrigadeRunWithAClientThatGrantsNoToolsTest(RunTestCase):
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
class BrigadeRunOfAProjectTest(RunTestCase):
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

    def test_should_exit_1_naming_a_project_role_binding_with_no_name(self):
        # Arrange
        self.register('ROLE "build"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr), (1, "brigade run: @PROJECT.shop has ROLE build, not slot=name\n")
        )

    def test_should_resolve_the_role_a_project_binds_to_an_agent_entity_of_the_instructions_corpus(self):
        # Arrange
        instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{instructions.root}"\n')
        self.record("planner", DONE_RESULT)
        self.register('ROLE "build=planner"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        front_matter = (self.runs / json.loads(completed.stdout)["run"] / "role.md").read_text().splitlines()[:9]
        self.assertEqual(
            front_matter,
            [
                "---",
                "name: planner",
                "slot: build",
                "work: the plan of a wave; the order of its tasks",
                "reasoning: deep",
                "capabilities: read, shell",
                "budget: 40",
                "returns: the wave plan; the blockers",
                "---",
            ],
        )

    def test_should_resolve_a_project_role_the_instructions_corpus_lacks_among_the_built_in_roles(self):
        # Arrange
        instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{instructions.root}"\n')
        self.record("verifier", DONE_RESULT)
        self.register('ROLE "build=verifier"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role"], "verifier")

    @unittest.skipIf(os.geteuid() == 0, "root reads what the permissions refuse")
    def test_should_exit_1_with_the_stderr_of_awawa_when_the_instructions_corpus_is_unreadable(self):
        # Arrange
        instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        agents = instructions.root / "agents.awawa"
        agents.chmod(0o000)
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{instructions.root}"\n')
        self.record("verifier", DONE_RESULT)
        self.register('ROLE "build=verifier"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(
            f"brigade run: awawa show @AGENT.verifier --json {instructions.root} exited 2: ", completed.stderr
        )
        self.assertIn(str(agents), completed.stderr)

    @unittest.skipIf(os.geteuid() == 0, "root reads what the permissions refuse")
    def test_should_launch_no_client_when_the_instructions_corpus_is_unreadable(self):
        # Arrange
        instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        (instructions.root / "agents.awawa").chmod(0o000)
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{instructions.root}"\n')
        self.record("verifier", DONE_RESULT)
        self.register('ROLE "build=verifier"')

        # Act
        self.run_slot()

        # Assert
        self.assertEqual(self.read_events("run.finished"), [])

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
        (self.machine.corpus / "policies.awawa").write_text(
            "POLICY shop_policy\n\tPROJECT @PROJECT.shop\n\tHANDOVERS 1\n"
        )

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 2)

    def test_should_take_the_handovers_of_the_policy_of_its_own_project_only(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", TURN_LIMIT_RESULT)
        self.register()
        (self.machine.corpus / "policies.awawa").write_text(
            'PROJECT depot\n\tPATH "/srv/depot"\n\tMAIN "main"\n\tSTATUS active\n\n'
            "POLICY a_depot_policy\n\tPROJECT @PROJECT.depot\n\tHANDOVERS 0\n\n"
            "POLICY shop_policy\n\tPROJECT @PROJECT.shop\n\tHANDOVERS 1\n"
        )

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 2)

    def write_role_file(self, directory: Path, name: str, slot: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.md").write_text(MACHINE_BUILDER.format(name=name, slot=slot))


REFUSED_RUN = "20261006T120000Z-b57000"
SEGMENT_REFUSED_RUN = "20261006T120000Z-b57010"
DETACHED_REFUSED_RUN = "20261006T120000Z-b57020"


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeRunWhereTheMachineRefusesTheRunsDirectoryTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.runs.mkdir(parents=True)

    def tearDown(self):
        self.runs.chmod(0o700)
        super().tearDown()

    def test_should_exit_1_naming_the_run_directory_it_cannot_create(self):
        # Arrange
        self.runs.chmod(0o500)

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--run-id", REFUSED_RUN
        )

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade run: cannot write {self.runs / REFUSED_RUN}: Permission denied\n"),
        )


class BrigadeRunOverAnEntryOfItsRunDirectoryItCannotWriteTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

    def run_deliver(self, run_id: str, *options: str):
        return self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--run-id", run_id, *options
        )

    def test_should_exit_1_naming_the_file_of_the_run_it_cannot_write(self):
        rows = [
            ("20261006T120000Z-b57001", "pid", ()),
            ("20261006T120000Z-b57002", "role.md", ()),
            ("20261006T120000Z-b57003", "progress.md", ()),
            ("20261006T120000Z-b57004", "segments/1/brief.md", ()),
            ("20261006T120000Z-b57005", "segments/1/stdout.log", ()),
            ("20261006T120000Z-b57006", "segments/1/stderr.log", ()),
            ("20261006T120000Z-b57007", "brigade.log", ("--detach",)),
        ]
        for run_id, entry, options in rows:
            with self.subTest(entry=entry):
                # Arrange
                (self.runs / run_id / entry).mkdir(parents=True)

                # Act
                completed = self.run_deliver(run_id, *options)

                # Assert
                self.assertEqual(
                    (completed.returncode, completed.stdout, completed.stderr),
                    (1, "", f"brigade run: cannot write {self.runs / run_id / entry}: Is a directory\n"),
                )

    def test_should_exit_1_naming_the_segment_directory_it_cannot_create(self):
        # Arrange
        segments = self.runs / SEGMENT_REFUSED_RUN / "segments"
        segments.parent.mkdir(parents=True)
        segments.write_text("")

        # Act
        completed = self.run_deliver(SEGMENT_REFUSED_RUN)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade run: cannot write {segments / '1'}: Not a directory\n"),
        )


class BrigadeRunDetachedWhereTheMachineRefusesASegmentTest(RunTestCase):
    def test_should_log_the_write_refused_to_the_detached_run_and_leave_it_dead(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_directory = self.runs / DETACHED_REFUSED_RUN
        run_directory.mkdir(parents=True)
        (run_directory / "segments").write_text("")

        # Act
        started = self.run_brigade(
            "run",
            str(self.procedure),
            "--slot",
            "build",
            "--cwd",
            str(self.workspace),
            "--run-id",
            DETACHED_REFUSED_RUN,
            "--detach",
            "--json",
        )

        # Assert
        self.assertEqual(started.returncode, 0, started.stderr)
        self.wait_for_exit(json.loads(started.stdout)["pid"])
        listed = self.run_brigade("runs", "list", "--json")
        self.assertEqual(
            ((run_directory / "brigade.log").read_text(), json.loads(listed.stdout)["runs"][0]["state"]),
            (f"brigade run: cannot write {run_directory / 'segments' / '1'}: Not a directory\n", "dead"),
        )


ENVIRONMENT_CLAUDE = Path(__file__).resolve().parent / "fixtures" / "executables" / "claude-environment"
ACCOUNTS_GH = Path(__file__).resolve().parent / "fixtures" / "executables" / "gh-accounts"
BOUND_SLOTS = (
    'client = "claude-code"\nforge_attempts = 1\n[forge_accounts]\nbuild = "octo-builder"\nverify = "refused-bot"\n'
)
BOUND_SLOTS_READ_TWICE = (
    'client = "claude-code"\nforge_attempts = 2\n[forge_accounts]\nbuild = "octo-builder"\nverify = "refused-bot"\n'
)


class ForgeAccountRunTestCase(RunTestCase):
    def setUp(self):
        super().setUp()
        self.environment_record = Path(self.root.name) / "environment.txt"
        self.gh_record = Path(self.root.name) / "gh.txt"
        self.environment = {
            **self.machine.describe_environment(),
            "PATH": os.pathsep.join([str(ENVIRONMENT_CLAUDE), str(ACCOUNTS_GH), os.environ["PATH"]]),
            "BRIGADE_ENVIRONMENT_RECORD": str(self.environment_record),
            "BRIGADE_GH_RECORD": str(self.gh_record),
        }

    def run_slot(self, slot: str, *options: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "run",
            str(self.procedure),
            "--slot",
            slot,
            "--cwd",
            str(self.workspace),
            *options,
            environment=self.environment,
        )


class BrigadeRunOfASlotBoundToALoginTest(ForgeAccountRunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(BOUND_SLOTS)

    def test_should_hand_the_client_segment_the_token_of_the_login_of_its_slot(self):
        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(
            (completed.returncode, self.environment_record.read_text()),
            (0, "token-of-octo-builder\n"),
            completed.stderr,
        )

    def test_should_write_the_token_nowhere(self):
        # Act
        completed = self.run_slot("build", "--verbose", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("token-of-", completed.stdout + completed.stderr + self.read_every_state_file())

    def test_should_write_the_token_nowhere_when_the_run_is_detached(self):
        # Act
        started = self.run_slot("build", "--detach", "--verbose", "--json")

        # Assert
        self.assertEqual(started.returncode, 0, started.stderr)
        self.wait_for_exit(json.loads(started.stdout)["pid"])
        self.assertNotIn("token-of-", started.stdout + started.stderr + self.read_every_state_file())


class BrigadeRunOfASlotWhoseLoginHasNoTokenTest(ForgeAccountRunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(BOUND_SLOTS)

    def test_should_stop_on_an_error_naming_the_login_and_the_attempts(self):
        # Act
        completed = self.run_slot("verify")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade run: gh printed no token for the login refused-bot, bound to verify, after 1 attempt\n"),
        )

    def test_should_record_the_login_unavailable_in_the_ledger(self):
        # Act
        self.run_slot("verify")

        # Assert
        self.assertEqual(
            self.read_events("forge_account.unavailable"),
            [
                {
                    "schema_version": 1,
                    "ts": mock.ANY,
                    "event": "forge_account.unavailable",
                    "login": "refused-bot",
                    "key": "verify",
                }
            ],
        )

    def test_should_start_no_run_after_reading_the_token_forge_attempts_times(self):
        # Arrange
        self.machine.write_configuration(BOUND_SLOTS_READ_TWICE)

        # Act
        self.run_slot("verify", "--detach")

        # Assert
        self.assertEqual(
            (self.gh_record.read_text().splitlines(), list(self.runs.glob("*"))),
            (["auth token --hostname github.com --user refused-bot"] * 2, []),
        )


class BrigadeRunOfASlotBoundToNoLoginTest(ForgeAccountRunTestCase):
    def test_should_hand_the_client_segment_no_token(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\n')

        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(
            (completed.returncode, self.environment_record.read_text()), (0, "no GH_TOKEN\n"), completed.stderr
        )
