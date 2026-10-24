import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, FINISHING_CLIENT, TURN_LIMIT_RESULT, RunTestCase
from tests.cli.stop_process import stop_process
from tests.cli.temporary_instructions import TemporaryInstructions
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, REPOSITORY_ROOT
from tests.cli.temporary_project import TemporaryProject
from tests.process_launcher import ProcessLauncher

NOT_UTF_8 = b"\xff\n"
RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"
INSTANT_PATTERN = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"
BUILT_IN_BUILDER = REPOSITORY_ROOT / "brigade" / "roles" / "data" / "builder.md"
RECORDING_CLAUDE = Path(__file__).resolve().parent / "fixtures" / "executables" / "claude-recording"
CLAUDE_AFTER_TASK_NOTIFICATION = (
    Path(__file__).resolve().parent / "fixtures" / "executables" / "claude-after-task-notification"
)
NOT_IN_A_WAVE = "not launched by a wave"
NOT_FOR_A_TASK = "not launched for a task"
CUT = "cut at the wall-time limit"
STOPPED = "stopped by a signal"
STOP_WAIT_S = 60
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
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
from tests.list_file_paths import list_file_paths


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
                    "task": NOT_FOR_A_TASK,
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
            list_file_paths(run_directory),
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
            f"The progress is the Markdown file {run_directory / 'progress.md'}.\n\n"
            "- one entry per major step: what it did in one line, the facts it established, one line each and five"
            " at most, and the next step as the procedure names it, complete at the end\n"
            "- a fact is what the next segment needs and no command gives back\n"
            "- never command output, a diff, the course of the step, a restatement of the brief or a fact an earlier"
            " entry holds\n"
            "- a handover entry holds what remains, one line per step not done, and the next step\n\n"
            "# End of segment\n\n"
            "End your final message on one of these lines: brigade-end: done once the work is delivered,"
            " brigade-end: handed_over when a next segment resumes it from the progress file,"
            " brigade-end: blocked when it waits for a ruling.\n",
        )

    def test_should_keep_the_package_of_the_resolved_role(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual((run_directory / "role.md").read_text(), BUILT_IN_BUILDER.read_text())

    def test_should_keep_as_result_of_the_segment_and_of_the_run_the_line_the_ledger_appended(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        [finished] = self.read_events("run.finished")
        self.assertEqual(json.loads((run_directory / "segments" / "1" / "result.json").read_text()), finished)
        self.assertEqual(json.loads((run_directory / "result.json").read_text()), finished)


class BrigadeRunOfATaskOfAWaveTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

    def run_deliver(self, *options: str):
        return self.run_brigade(
            "run",
            str(self.procedure),
            "--slot",
            "build",
            "--cwd",
            str(self.workspace),
            "--wave",
            "shop_w3",
            "--task",
            "S3",
            *options,
        )

    def test_should_record_the_wave_and_the_task_in_the_run_record(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_record = self.read_run_record(json.loads(completed.stdout)["run"])
        self.assertEqual(run_record["wave"], "shop_w3")
        self.assertEqual(run_record["task"], "S3")

    def test_should_carry_the_wave_and_the_task_in_the_finished_run_with_no_reason_for_them(self):
        # Act
        completed = self.run_deliver("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["wave"], "shop_w3")
        self.assertEqual(finished["task"], "S3")
        self.assertEqual(
            finished["nulls"],
            {
                "project": "no project given",
                "total_steps": "the client reads no transcript",
                "error_class": "the run did not fail",
            },
        )

    def test_should_carry_the_wave_and_the_task_through_a_detached_run(self):
        # Act
        completed = self.wait_for_the_detached_run(self.run_deliver("--detach"))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["wave"], "shop_w3")
        self.assertEqual(finished["task"], "S3")


class BrigadeRunWithOneOfTheWaveAndTheTaskTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

    def run_deliver(self, *options: str):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), *options)

    def test_should_explain_the_missing_task_of_a_run_of_a_wave(self):
        # Act
        completed = self.run_deliver("--wave", "shop_w3")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["wave"], "shop_w3")
        self.assertEqual(finished["task"], None)
        self.assertEqual(
            finished["nulls"],
            {
                "project": "no project given",
                "task": "not launched for a task",
                "total_steps": "the client reads no transcript",
                "error_class": "the run did not fail",
            },
        )

    def test_should_explain_the_missing_wave_of_a_run_of_a_task(self):
        # Act
        completed = self.run_deliver("--task", "S3")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["wave"], None)
        self.assertEqual(finished["task"], "S3")
        self.assertEqual(
            finished["nulls"],
            {
                "project": "no project given",
                "wave": "not launched by a wave",
                "total_steps": "the client reads no transcript",
                "error_class": "the run did not fail",
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
                {
                    "role": "user",
                    "timestamp": None,
                    "content": "Deliver B83.",
                    "tool_calls": 0,
                    "id": None,
                    "usage": None,
                },
                {"role": "assistant", "timestamp": None, "content": [], "tool_calls": 2, "id": None, "usage": None},
            ],
            "subagents": [
                {
                    "messages": [
                        {
                            "role": "assistant",
                            "timestamp": None,
                            "content": [],
                            "tool_calls": 1,
                            "id": None,
                            "usage": None,
                        }
                    ]
                },
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
        self.machine.write_configuration('client = "claude-code"\ndocument = "markdown"\n')
        self.brief = self.workspace / "brief.md"
        self.brief.write_text("Deliver B71.\n")

    def test_should_hand_the_client_the_role_file_and_grant_it_the_progress_file(self):
        # Arrange
        environment = {
            **self.machine.describe_environment(),
            "PATH": os.pathsep.join([str(RECORDING_CLAUDE), self.machine.search_path]),
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
        self.assertEqual(completed.returncode, 3, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        arguments = (run_directory / "progress.md").read_text().splitlines()
        self.assertRegex(arguments.pop(7), UUID_PATTERN)
        self.assertRegex(arguments.pop(), r'^\{"hooks": \{"PostToolUse": .*-ge \d+ \]')
        self.assertEqual(
            arguments,
            [
                "--print",
                "--output-format",
                "stream-json",
                "--verbose",
                "--permission-mode",
                "dontAsk",
                "--session-id",
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
                "--settings",
            ],
        )

    def test_should_keep_as_result_of_a_segment_ended_after_a_task_notification_the_line_the_ledger_appended(self):
        # Arrange
        environment = {
            **self.machine.describe_environment(),
            "PATH": os.pathsep.join([str(CLAUDE_AFTER_TASK_NOTIFICATION), self.machine.search_path]),
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
        self.assertEqual(completed.returncode, 3, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        [finished] = self.read_events("run.finished")
        self.assertEqual(json.loads((run_directory / "segments" / "1" / "result.json").read_text()), finished)


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


class BrigadeRunOfTheShippedWavePlanProcedureTest(RunTestCase):
    def test_should_resolve_it_for_the_planner_with_the_capability_to_write_its_plan(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("planner", DONE_RESULT)

        # Act
        completed = self.run_brigade(
            "run", "wave-plan", "--slot", "plan", "--cwd", str(self.workspace), "request=R1", "--json"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = json.loads(completed.stdout)["run"]
        self.assertEqual(
            self.read_run_record(run_id),
            {
                "schema_version": 1,
                "run": run_id,
                "procedure": "wave-plan",
                "procedure_path": str(REPOSITORY_ROOT / "brigade" / "runs" / "data" / "procedures" / "wave-plan.md"),
                "slot": "plan",
                "role": "planner",
                "role_source": "built-in",
                "client": "fake",
                "project": None,
                "cwd": str(self.workspace),
                "worktree": str(self.workspace),
                "capabilities": ["read", "write", "shell"],
                "budget": 30,
                "wall_limit_s": 1140,
                "arguments": {"request": "R1"},
                "wave": None,
                "task": None,
                "brief": None,
            },
        )


class BrigadeRunOfTheShippedVerifyPrProcedureTest(RunTestCase):
    def test_should_resolve_it_for_the_reviewer_with_the_capabilities_to_read_and_judge(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("reviewer", DONE_RESULT)

        # Act
        completed = self.run_brigade(
            "run", "verify-pr", "--slot", "review", "--cwd", str(self.workspace), "pr=42", "task=@TASK.S3", "--json"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = json.loads(completed.stdout)["run"]
        self.assertEqual(
            self.read_run_record(run_id),
            {
                "schema_version": 1,
                "run": run_id,
                "procedure": "verify-pr",
                "procedure_path": str(REPOSITORY_ROOT / "brigade" / "runs" / "data" / "procedures" / "verify-pr.md"),
                "slot": "review",
                "role": "reviewer",
                "role_source": "built-in",
                "client": "fake",
                "project": None,
                "cwd": str(self.workspace),
                "worktree": str(self.workspace),
                "capabilities": ["read", "shell"],
                "budget": 40,
                "wall_limit_s": 1500,
                "arguments": {"pr": "42", "task": "@TASK.S3"},
                "wave": None,
                "task": None,
                "brief": None,
            },
        )


class BrigadeRunOfAProcedureOffItsDeclarationTest(RunTestCase):
    def test_should_exit_1_naming_the_procedure_and_what_it_lacks(self):
        # Arrange
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
        # Arrange
        missing = self.workspace / "missing"
        rows = [
            ("a directory that does not exist", ["--cwd", str(missing)], f"no directory {missing}"),
            (
                "a brief that does not exist",
                ["--cwd", str(self.workspace), "--brief", str(missing)],
                f"no brief file {missing}",
            ),
            ("an argument with no key", ["--cwd", str(self.workspace), "=B06"], "the argument =B06 is not key=value"),
            ("a word with no separator", ["--cwd", str(self.workspace), "B06"], "the argument B06 is not key=value"),
        ]
        self.configure_fake(COUNTING_CLIENT)
        for case, options, refusal in rows:
            with self.subTest(case=case):
                # Act
                completed = self.run_brigade("run", str(self.procedure), "--slot", "build", *options)

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, f"brigade run: {refusal}\n")

    def test_should_exit_2_for_a_run_id_off_its_pattern(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--run-id", "latest"
        )

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stderr, "brigade run: latest is not a run id\n")

    def test_should_exit_1_when_config_toml_names_no_client(self):
        # Arrange
        configuration = self.machine.write_configuration("")

        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, f"brigade run: config.toml names no client: set the client key in {configuration}\n"
        )


class BrigadeRunOfKeyValueArgumentsAroundTheOptionsTest(RunTestCase):
    def test_should_hand_the_run_every_argument_wherever_it_stands_among_the_options(self):
        # Arrange
        rows = [
            ("after the options", ["--slot", "build", "a=1", "b=2"]),
            ("before the options", ["a=1", "b=2", "--slot", "build"]),
            ("on both sides of an option", ["a=1", "--slot", "build", "b=2"]),
        ]
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        for case, words in rows:
            with self.subTest(case=case):
                # Act
                completed = self.run_brigade("run", "--cwd", str(self.workspace), "--json", str(self.procedure), *words)

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                run_record = self.read_run_record(json.loads(completed.stdout)["run"])
                self.assertEqual(run_record["arguments"], {"a": "1", "b": "2"})


class BrigadeRunHelpTest(RunTestCase):
    def test_should_name_the_key_value_arguments_of_the_procedure(self):
        # Act
        completed = self.run_brigade("run", "--help")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("key=value", completed.stdout)


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
                "wave": None,
                "task": None,
                "brief": None,
            },
        )


class BrigadeRunOfTheReviewAndRemediateSlotsTest(RunTestCase):
    def test_should_keep_write_for_the_remediate_slot_alone(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("remediator", DONE_RESULT)
        self.record("reviewer", DONE_RESULT)
        self.procedure.write_text("---\ncapabilities: read, write, shell\nbudget: 75\n---\nAnswer the review.\n")

        for slot, role, capabilities in [
            ("remediate", "remediator", ["read", "write", "shell"]),
            ("review", "reviewer", ["read", "shell"]),
        ]:
            with self.subTest(slot=slot):
                # Act
                completed = self.run_brigade(
                    "run", str(self.procedure), "--slot", slot, "--cwd", str(self.workspace), "task=B06", "--json"
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
                        "slot": slot,
                        "role": role,
                        "role_source": "built-in",
                        "client": "fake",
                        "project": None,
                        "cwd": str(self.workspace),
                        "worktree": str(self.workspace),
                        "capabilities": capabilities,
                        "budget": 75,
                        "wall_limit_s": 2820,
                        "arguments": {"task": "B06"},
                        "wave": None,
                        "task": None,
                        "brief": None,
                    },
                )


class BrigadeRunDetachedTest(RunTestCase):
    def test_should_print_the_run_id_and_exit_0_while_the_run_finishes_in_the_background(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.wait_for_the_detached_run(
            self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--detach")
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = completed.stdout.strip()
        self.assertRegex(run_id, RUN_ID_PATTERN)
        self.assertRegex((self.runs / run_id / "pid").read_text(), r"^\d+ \d+ [0-9a-f-]{36}\n$")
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["run"], run_id)


class BrigadeRunStoppedBySignalTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + self.hold_the_client())
        self.record("builder", DONE_RESULT)

    def start_detached(self) -> str:
        started = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--detach"
        )
        return started.stdout.strip()

    def start_in_the_foreground(self) -> subprocess.Popen:
        brigade = ProcessLauncher.start(
            [
                sys.executable,
                str(CLONE_ENTRY_POINT),
                "run",
                str(self.procedure),
                "--slot",
                "build",
                "--cwd",
                str(self.workspace),
                "--json",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(brigade.wait)
        self.addCleanup(brigade.kill)
        return brigade

    def terminate(self, brigade_pid: int) -> None:
        os.kill(brigade_pid, signal.SIGTERM)
        self.wait_for_exit(brigade_pid)

    def terminate_and_list_the_runs(self, brigade_pid: int) -> list:
        self.terminate(brigade_pid)
        return self.list_the_runs()

    def test_should_stop_the_client_of_a_detached_run_sent_sigterm_and_list_the_run_finished_stopped(self):
        # Arrange
        run_id = self.start_detached()
        brigade_pid = self.read_run_pid(run_id)
        client_pid = self.wait_for_client(brigade_pid)
        (self.runs / run_id / "progress.md").write_text("step 1 done\n")

        # Act
        [listed] = self.terminate_and_list_the_runs(brigade_pid)

        # Assert
        self.assert_process_gone(client_pid)
        self.assertEqual(json.loads((self.runs / run_id / "result.json").read_text())["outcome"], "stopped")
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["outcome"], "stopped")
        self.assertEqual(listed["state"], "finished")
        self.assertEqual(listed["outcome"], "stopped")

    def test_should_stop_the_client_of_a_foreground_run_sent_sigint_and_exit_21(self):
        # Arrange
        brigade = self.start_in_the_foreground()
        client_pid = self.wait_for_client(brigade.pid)

        # Act
        stdout, stderr = stop_process(brigade, signal.SIGINT, STOP_WAIT_S)

        # Assert
        self.assertEqual(brigade.returncode, 21, stderr)
        self.assert_process_gone(client_pid)
        run_id = json.loads(stdout)["run"]
        self.assertEqual(json.loads(stdout)["outcome"], "stopped")
        self.assertEqual(json.loads((self.runs / run_id / "result.json").read_text())["outcome"], "stopped")

    def test_should_record_the_stop_in_the_finished_event_and_in_the_processes_of_the_run(self):
        # Arrange
        run_id = self.start_detached()
        brigade_pid = self.read_run_pid(run_id)
        self.wait_for_client(brigade_pid)

        # Act
        self.terminate(brigade_pid)

        # Assert
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["outcome"], "stopped")
        self.assertEqual(finished["exit"], None)
        self.assertEqual(finished["error_class"], None)
        self.assertEqual(
            finished["nulls"],
            {
                "project": "no project given",
                "wave": NOT_IN_A_WAVE,
                "task": NOT_FOR_A_TASK,
                "main_steps": "the client reads no transcript",
                "total_steps": "the client reads no transcript",
                "usage": "the client reads no transcript",
                "error_class": STOPPED,
                "exit": STOPPED,
            },
        )
        client_record = json.loads((self.runs / run_id / "processes.jsonl").read_text().splitlines()[-1])
        self.assertEqual(client_record["argv"][0], "sh")
        self.assertEqual(client_record["outcome"], "stopped")
        self.assertEqual(client_record["exit"], None)


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
        self.assertEqual(completed.returncode, 12, completed.stderr)
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
                "outcome": "turn_limit",
            },
        )

    def test_should_write_one_finished_event_per_segment(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 12, completed.stderr)
        self.assertEqual(len(self.read_events("run.finished")), 3)

    def test_should_give_the_progress_file_as_the_first_context_of_the_next_segment(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 12, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual(
            (run_directory / "segments" / "2" / "brief.md").read_text(),
            "# Progress so far\n\n"
            "step 1 done\n\n"
            "# Procedure deliver\n\n"
            "Deliver the task the brief names.\n\n"
            "# Progress file\n\n"
            f"The progress is the Markdown file {run_directory / 'progress.md'}.\n\n"
            "- one entry per major step: what it did in one line, the facts it established, one line each and five"
            " at most, and the next step as the procedure names it, complete at the end\n"
            "- a fact is what the next segment needs and no command gives back\n"
            "- never command output, a diff, the course of the step, a restatement of the brief or a fact an earlier"
            " entry holds\n"
            "- a handover entry holds what remains, one line per step not done, and the next step\n\n"
            "# End of segment\n\n"
            "End your final message on one of these lines: brigade-end: done once the work is delivered,"
            " brigade-end: handed_over when a next segment resumes it from the progress file,"
            " brigade-end: blocked when it waits for a ruling.\n",
        )

    def test_should_not_relaunch_a_segment_ended_on_the_step_cap_with_an_empty_progress_file(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 12, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 1)

    def test_should_record_the_budget_exceeded_and_the_step_cap_reached_naming_the_procedure_and_the_run(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 12, completed.stderr)
        run = json.loads(completed.stdout)["run"]
        [exceeded, reached] = self.read_events("signal.recorded")
        self.assertRegex(exceeded.pop("ts"), INSTANT_PATTERN)
        self.assertRegex(reached.pop("ts"), INSTANT_PATTERN)
        self.assertEqual(
            [exceeded, reached],
            [
                {
                    "schema_version": 1,
                    "event": "signal.recorded",
                    "signal": "budget_exceeded",
                    "project": None,
                    "procedure": "deliver",
                    "run": run,
                    "segment": 1,
                    "budget": 75,
                    "steps": 94,
                },
                {
                    "schema_version": 1,
                    "event": "signal.recorded",
                    "signal": "budget_reached",
                    "project": None,
                    "procedure": "deliver",
                    "run": run,
                    "segment": 1,
                    "budget": 75,
                },
            ],
        )


class BrigadeRunOverItsBudgetTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)

    def run_deliver(self):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json")

    def test_should_end_done_and_record_the_steps_over_the_budget(self):
        # Arrange
        self.record("builder", {**DONE_RESULT, "steps": 76})

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["outcome"], "done")
        [signal] = self.read_events("signal.recorded")
        self.assertRegex(signal.pop("ts"), INSTANT_PATTERN)
        self.assertEqual(
            signal,
            {
                "schema_version": 1,
                "event": "signal.recorded",
                "signal": "budget_exceeded",
                "project": None,
                "procedure": "deliver",
                "run": json.loads(completed.stdout)["run"],
                "segment": 1,
                "budget": 75,
                "steps": 76,
            },
        )

    def test_should_record_no_signal_for_a_segment_at_exactly_its_budget(self):
        # Arrange
        self.record("builder", {**DONE_RESULT, "steps": 75})

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_events("signal.recorded"), [])


class BrigadeRunOnTheClockTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + self.hold_the_client(), keys="seconds_per_step = 0.2\n")
        self.record("builder", DONE_RESULT)
        self.quick = self.procedure.with_name("quick.md")
        self.quick.write_text(QUICK_PROCEDURE)

    def run_quick(self):
        return self.run_brigade("run", str(self.quick), "--slot", "build", "--cwd", str(self.workspace), "--json")

    def test_should_cut_the_client_at_its_wall_time_limit(self):
        # Act
        completed = self.run_quick()

        # Assert
        self.assertEqual(completed.returncode, 11, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertRegex(finished.pop("ts"), INSTANT_PATTERN)
        self.assertLess(finished.pop("duration_ms"), 10000)
        self.assertRegex(finished.pop("session"), UUID_PATTERN)
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
                    "task": NOT_FOR_A_TASK,
                    "main_steps": "the client reads no transcript",
                    "total_steps": "the client reads no transcript",
                    "usage": "the client reads no transcript",
                    "error_class": CUT,
                    "exit": CUT,
                },
                "message": "cut at the wall-time limit of 0.4 s",
            },
        )


class BrigadeRunAtTheSoftLimitTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(
            'features = "step_count,tool_grants,graceful_stop"\nprogress = "step 1 done"\n',
            keys="seconds_per_step = 2\nsoft_limit_margin_s = 3.5\n",
        )
        self.record("builder", {**DONE_RESULT, "outcome": "soft_limit", "steps": 1})
        (self.recordings / "builder.resumed.json").write_text(json.dumps({**DONE_RESULT, "steps": 1}))
        self.quick = self.procedure.with_name("quick.md")
        self.quick.write_text(QUICK_PROCEDURE)

    def run_quick(self):
        return self.run_brigade("run", str(self.quick), "--slot", "build", "--cwd", str(self.workspace), "--json")

    def test_should_keep_the_result_of_a_segment_stopped_at_the_soft_limit_then_resume_and_exit_0(self):
        # Act
        completed = self.run_quick()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["segments"], 2)
        self.assertEqual(document["outcome"], "done")
        first, _ = self.read_events("run.finished")
        self.assertEqual(first["outcome"], "soft_limit")
        self.assertEqual(first["exit"], 0)
        self.assertEqual(first["session"], "fake-session")
        self.assertEqual(first["cost_usd"], 0.42)

    def test_should_record_that_the_clock_ended_the_segment_stopped_at_the_soft_limit(self):
        # Act
        completed = self.run_quick()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [signal] = self.read_events("signal.recorded")
        self.assertRegex(signal.pop("ts"), INSTANT_PATTERN)
        self.assertEqual(
            signal,
            {
                "schema_version": 1,
                "event": "signal.recorded",
                "signal": "wall_limit_reached",
                "project": None,
                "procedure": "quick",
                "run": json.loads(completed.stdout)["run"],
                "segment": 1,
                "budget": 1,
                "wall_limit_s": 4,
            },
        )

    def test_should_cut_at_the_wall_time_limit_a_client_declaring_no_graceful_stop(self):
        # Arrange
        self.configure_fake(
            COUNTING_CLIENT + self.hold_the_client(), keys="seconds_per_step = 0.2\nsoft_limit_margin_s = 0.1\n"
        )

        # Act
        completed = self.run_quick()

        # Assert
        self.assertEqual(completed.returncode, 11, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["outcome"], "wall_limit")


class BrigadeRunEndDeclarationTest(RunTestCase):
    def run_deliver(self):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json")

    def record_resumed(self, role: str, result: dict) -> None:
        (self.recordings / f"{role}.resumed.json").write_text(json.dumps(result))

    def test_should_exit_0_after_one_segment_declaring_done(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 1)

    def test_should_relaunch_a_segment_handed_over_and_exit_0_once_the_next_declares_done(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", {**DONE_RESULT, "outcome": "handed_over"})
        self.record_resumed("builder", DONE_RESULT)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["segments"], 2)
        self.assertEqual(document["outcome"], "done")
        second_brief = (self.runs / document["run"] / "segments" / "2" / "brief.md").read_text()
        self.assertRegex(second_brief, r"\A# Progress so far\n\nstep 1 done\n")

    def test_should_exit_20_after_the_last_hand_over_of_a_run_handed_over_at_every_segment(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", {**DONE_RESULT, "outcome": "handed_over"})

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 20, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["segments"], 3)
        self.assertEqual(document["outcome"], "handed_over")

    def test_should_exit_10_after_one_segment_declaring_blocked_whatever_its_progress(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", {**DONE_RESULT, "outcome": "blocked"})

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 10, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 1)

    def test_should_relaunch_an_undeclared_segment_and_exit_3_after_the_last_hand_over(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", {**DONE_RESULT, "outcome": "undeclared"})

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 3, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["segments"], 3)
        self.assertEqual(document["outcome"], "undeclared")

    def test_should_exit_3_after_one_undeclared_segment_with_an_empty_progress_file(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", {**DONE_RESULT, "outcome": "undeclared"})

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 1)

    def test_should_exit_1_after_one_segment_ended_on_a_client_error(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n')
        self.record("builder", {**TURN_LIMIT_RESULT, "error_class": "execution", "message": "the client crashed"})

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["segments"], 1)
        self.assertEqual(document["outcome"], "failed")

    def test_should_record_a_signal_naming_how_a_segment_ended_without_delivery(self):
        # Arrange
        rows = [("handed over", "handed_over"), ("undeclared", "undeclared")]
        for case, outcome in rows:
            with self.subTest(case=case):
                # Arrange
                self.configure_fake(COUNTING_CLIENT)
                self.record("builder", {**DONE_RESULT, "outcome": outcome})
                shutil.rmtree(self.ledger, ignore_errors=True)

                # Act
                completed = self.run_deliver()

                # Assert
                [signal] = self.read_events("signal.recorded")
                self.assertRegex(signal.pop("ts"), INSTANT_PATTERN)
                self.assertEqual(
                    signal,
                    {
                        "schema_version": 1,
                        "event": "signal.recorded",
                        "signal": outcome,
                        "project": None,
                        "procedure": "deliver",
                        "run": json.loads(completed.stdout)["run"],
                        "segment": 1,
                        "budget": 75,
                    },
                )

    def test_should_end_the_run_on_turn_limit_in_its_list_its_result_and_its_last_finished_event(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", TURN_LIMIT_RESULT)
        run_id = json.loads(self.run_deliver().stdout)["run"]

        # Act
        [listed] = self.list_the_runs()

        # Assert
        self.assertEqual(listed["outcome"], "turn_limit")
        self.assertEqual(json.loads((self.runs / run_id / "result.json").read_text())["outcome"], "turn_limit")
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["outcome"], "turn_limit")


class BrigadeRunOfAClientAnsweringParseResultOutsideItsContractTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.record(
            "builder",
            {
                "schema_version": 1,
                "steps": 12,
                "usage": None,
                "session_id": "fake-session",
                "duration_ms": 61000,
                "cost_usd": 0.42,
                "error_class": None,
                "reset": None,
                "message": None,
            },
        )

    def run_deliver(self):
        return self.run_brigade("run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json")

    def test_should_exit_1_after_one_segment_ended_failed(self):
        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["segments"], 1)
        self.assertEqual(document["outcome"], "failed")

    def test_should_write_the_result_of_the_run_naming_the_adapter_the_operation_and_the_problem(self):
        # Act
        completed = self.run_deliver()

        # Assert
        result = json.loads((self.runs / json.loads(completed.stdout)["run"] / "result.json").read_text())
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["message"], "client adapter fake answered parse-result: lacks the key outcome")

    def test_should_append_the_end_of_the_run_on_the_outcome_failed(self):
        # Act
        self.run_deliver()

        # Assert
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["outcome"], "failed")


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

    def test_should_record_no_budget_signal_for_steps_it_does_not_count(self):
        # Arrange
        self.record("builder", {**DONE_RESULT, "steps": 76})

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--json"
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_events("signal.recorded"), [])


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

    def test_should_take_no_lock_of_worktrees_for_a_reading_slot_run_outside_any_project(self):
        # Arrange
        self.record("explorer", DONE_RESULT)

        # Act
        completed = self.run_slot("explore")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(list((self.runs.parent / "locks").glob("worktrees-*")), [])

    def test_should_run_a_writing_slot_in_the_directory_it_is_given(self):
        # Arrange
        self.record("builder", DONE_RESULT)

        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_run_record(json.loads(completed.stdout)["run"])["worktree"], str(self.project.path))


class BrigadeRunOfAReadingSlotOfAProjectTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.install_awawa(self)
        initialised = self.machine.run_init()
        self.assertEqual(initialised.returncode, 0, initialised.stderr)
        self.configure_fake('features = "step_count"\n')
        self.project = TemporaryProject(self.workspace / "shop", self.machine.describe_environment())
        self.project.run_git("commit", "--quiet", "--allow-empty", "-m", "initial")
        (self.machine.corpus / "projects.awawa").write_text(
            f'PROJECT shop\n\tPATH "{self.project.path}"\n\tMAIN "main"\n\tSTATUS active\n'
        )
        self.record("explorer", DONE_RESULT)

    def test_should_take_the_lock_of_the_worktrees_of_the_project_around_its_disposable_worktree(self):
        # Act
        completed = self.run_brigade("run", str(self.procedure), "--slot", "explore", "--project", "shop", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((self.runs.parent / "locks" / "worktrees-shop.lock").is_file())


class BrigadeRunOfAProjectTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.install_awawa(self)
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
        return self.run_brigade(
            "run",
            str(self.procedure),
            "--slot",
            slot,
            "--project",
            "shop",
            "--json",
            path_directories=(FINISHING_CLIENT,),
        )

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

    def test_should_run_with_the_client_the_slot_clients_table_binds_over_the_client_the_project_names(self):
        # Arrange
        self.configure_fake(f'{COUNTING_CLIENT}[slot_clients]\nbuild = "finishing"\n')
        self.register('CLIENT "fake"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["client"], "finishing")

    def test_should_bind_the_slot_to_the_role_the_project_names(self):
        # Arrange
        self.register('ROLE "build=reviewer"')
        self.record("reviewer", DONE_RESULT)

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role"], "reviewer")

    def test_should_exit_1_naming_a_project_role_binding_with_no_name(self):
        # Arrange
        self.register('ROLE "build"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade run: @PROJECT.shop has ROLE build, not slot=name\n")

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
        self.record("reviewer", DONE_RESULT)
        self.register('ROLE "build=reviewer"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["role"], "reviewer")

    def test_should_exit_1_with_the_stderr_of_awawa_when_the_instructions_corpus_is_unreadable(self):
        # Arrange
        instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        agents = instructions.root / "agents.awawa"
        agents.write_bytes(NOT_UTF_8)
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{instructions.root}"\n')
        self.record("reviewer", DONE_RESULT)
        self.register('ROLE "build=reviewer"')

        # Act
        completed = self.run_slot()

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(
            f"brigade run: awawa show @AGENT.reviewer --json {instructions.root} exited 2: ", completed.stderr
        )
        self.assertIn(str(agents), completed.stderr)

    def test_should_launch_no_client_when_the_instructions_corpus_is_unreadable(self):
        # Arrange
        instructions = TemporaryInstructions(Path(self.root.name) / "instructions")
        (instructions.root / "agents.awawa").write_bytes(NOT_UTF_8)
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{instructions.root}"\n')
        self.record("reviewer", DONE_RESULT)
        self.register('ROLE "build=reviewer"')

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
        self.assertEqual(completed.returncode, 12, completed.stderr)
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
        self.assertEqual(completed.returncode, 12, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 2)

    def write_role_file(self, directory: Path, name: str, slot: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.md").write_text(MACHINE_BUILDER.format(name=name, slot=slot))


REFUSED_RUN = "20261006T120000Z-b57000"
SEGMENT_REFUSED_RUN = "20261006T120000Z-b57010"
DETACHED_REFUSED_RUN = "20261006T120000Z-b57020"


class BrigadeRunWhereAFileStandsForTheRunsDirectoryTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT)
        self.runs.parent.mkdir(parents=True)

    def test_should_exit_1_naming_the_run_directory_it_cannot_create(self):
        # Arrange
        self.runs.write_text("")

        # Act
        completed = self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--run-id", REFUSED_RUN
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, f"brigade run: cannot write {self.runs / REFUSED_RUN}: Not a directory\n")


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
        # Arrange
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
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stdout, "")
                self.assertEqual(
                    completed.stderr, f"brigade run: cannot write {self.runs / run_id / entry}: Is a directory\n"
                )

    def test_should_exit_1_naming_the_segment_directory_it_cannot_create(self):
        # Arrange
        segments = self.runs / SEGMENT_REFUSED_RUN / "segments"
        segments.parent.mkdir(parents=True)
        segments.write_text("")

        # Act
        completed = self.run_deliver(SEGMENT_REFUSED_RUN)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, f"brigade run: cannot write {segments / '1'}: Not a directory\n")


class BrigadeRunDetachedWhereTheMachineRefusesASegmentTest(RunTestCase):
    def run_detached_and_list_the_runs(self, *arguments: str) -> tuple:
        return self.wait_for_the_detached_run(self.run_brigade(*arguments)), self.list_the_runs()

    def test_should_log_the_write_refused_to_the_detached_run_and_leave_it_dead(self):
        # Arrange
        self.configure_fake(COUNTING_CLIENT)
        self.record("builder", DONE_RESULT)
        run_directory = self.runs / DETACHED_REFUSED_RUN
        run_directory.mkdir(parents=True)
        (run_directory / "segments").write_text("")

        # Act
        started, [listed] = self.run_detached_and_list_the_runs(
            "run",
            str(self.procedure),
            "--slot",
            "build",
            "--cwd",
            str(self.workspace),
            "--run-id",
            DETACHED_REFUSED_RUN,
            "--detach",
        )

        # Assert
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(
            (run_directory / "brigade.log").read_text(),
            f"brigade run: cannot write {run_directory / 'segments' / '1'}: Not a directory\n",
        )
        self.assertEqual(listed["state"], "dead")


ENVIRONMENT_CLAUDE = Path(__file__).resolve().parent / "fixtures" / "executables" / "claude-environment"
ACCOUNTS_GH = Path(__file__).resolve().parent / "fixtures" / "executables" / "gh-accounts"
BOUND_SLOTS = (
    'client = "claude-code"\nforge_attempts = 1\n[forge_accounts]\nbuild = "octo-builder"\nreview = "refused-bot"\n'
)
BOUND_SLOTS_READ_TWICE = (
    'client = "claude-code"\nforge_attempts = 2\n[forge_accounts]\nbuild = "octo-builder"\nreview = "refused-bot"\n'
)


class ForgeAccountRunTestCase(RunTestCase):
    def setUp(self):
        super().setUp()
        self.environment_record = Path(self.root.name) / "environment.txt"
        self.gh_record = Path(self.root.name) / "gh.txt"
        self.environment = {
            **self.machine.describe_environment(),
            "PATH": os.pathsep.join([str(ENVIRONMENT_CLAUDE), str(ACCOUNTS_GH), self.machine.search_path]),
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
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertEqual(self.environment_record.read_text(), "token-of-octo-builder\n", completed.stderr)

    def test_should_write_the_token_nowhere(self):
        # Act
        completed = self.run_slot("build", "--verbose", "--json")

        # Assert
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertNotIn("token-of-", completed.stdout + completed.stderr + self.read_every_state_file())

    def test_should_write_the_token_nowhere_when_the_run_is_detached(self):
        # Act
        started = self.wait_for_the_detached_run(self.run_slot("build", "--detach", "--verbose", "--json"))

        # Assert
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertNotIn("token-of-", started.stdout + started.stderr + self.read_every_state_file())


class BrigadeRunOfASlotWhoseLoginHasNoTokenTest(ForgeAccountRunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration(BOUND_SLOTS)

    def test_should_start_no_run_after_reading_the_token_forge_attempts_times(self):
        # Arrange
        self.machine.write_configuration(BOUND_SLOTS_READ_TWICE)

        # Act
        self.run_slot("review", "--detach")

        # Assert
        self.assertEqual(
            self.gh_record.read_text().splitlines(), ["auth token --hostname github.com --user refused-bot"] * 2
        )
        self.assertEqual(list(self.runs.glob("*")), [])


class BrigadeRunOfASlotBoundToNoLoginTest(ForgeAccountRunTestCase):
    def test_should_hand_the_client_segment_no_token(self):
        # Arrange
        self.machine.write_configuration('client = "claude-code"\ndocument = "markdown"\n')

        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertEqual(self.environment_record.read_text(), "no GH_TOKEN\n", completed.stderr)


PROGRESS_SCHEMA = (
    "SCHEMA STEP\n"
    '\tDESC "a step the run completed"\n'
    "\tFIELD DONE string\n"
    "\t\tREQUIRED\n"
    '\t\tDESC "what the step did, one line"\n'
    "\tFIELD FACT string\n"
    "\t\tREPEATABLE\n"
    '\t\tDESC "a fact the next run needs and no command gives back, five at most"\n'
    "\tFIELD NEXT string\n"
    "\t\tREQUIRED\n"
    '\t\tDESC "the step to resume at, as the procedure names it, or complete"\n'
    "\n"
    "SCHEMA HANDOVER\n"
    '\tDESC "the state of a run that hands over"\n'
    "\tFIELD FACT string\n"
    "\t\tREPEATABLE\n"
    '\t\tDESC "a fact no step holds, five at most"\n'
    "\tFIELD REMAINING string\n"
    "\t\tREQUIRED\n"
    "\t\tREPEATABLE\n"
    '\t\tDESC "a step not done, one per line"\n'
    "\tFIELD NEXT string\n"
    "\t\tREQUIRED\n"
    '\t\tDESC "the step to resume at, as the procedure names it"\n'
)
HANDED_OVER_RESULT = {**DONE_RESULT, "outcome": "handed_over"}
RUN_ID = "20261013T000000Z-b106a1"
STEP_ENTRY = 'progress = "STEP s1\\n\\tDONE \\"read the task\\"\\n\\tNEXT \\"section 3\\""\n'


class BrigadeRunProgressFormTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.install_awawa(self)

    def run_deliver(self):
        return self.run_brigade(
            "run", str(self.procedure), "--slot", "build", "--cwd", str(self.workspace), "--run-id", RUN_ID, "--json"
        )

    def test_should_keep_the_progress_as_an_awawa_corpus_holding_its_schema_alone_without_the_document_key(self):
        # Arrange
        self.record("builder", DONE_RESULT)
        self.configure_fake(COUNTING_CLIENT, document=None)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual((run_directory / "progress.awawa").read_text(), PROGRESS_SCHEMA)
        self.assertFalse((run_directory / "progress.md").exists())

    def test_should_keep_the_progress_as_an_empty_markdown_file_with_the_markdown_document(self):
        # Arrange
        self.record("builder", DONE_RESULT)
        self.configure_fake(COUNTING_CLIENT, document="markdown")

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_directory = self.runs / json.loads(completed.stdout)["run"]
        self.assertEqual((run_directory / "progress.md").read_text(), "")
        self.assertFalse((run_directory / "progress.awawa").exists())

    def test_should_relaunch_a_segment_that_hands_over_on_a_brief_opening_on_the_inventory_and_the_last_entity(self):
        # Arrange
        self.record("builder", HANDED_OVER_RESULT)
        self.configure_fake(COUNTING_CLIENT + STEP_ENTRY, document=None)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 20, completed.stderr)
        progress = self.runs / json.loads(completed.stdout)["run"] / "progress.awawa"
        opening, _, _ = (progress.parent / "segments" / "2" / "brief.md").read_text().partition("# Procedure deliver")
        self.assertEqual(
            opening,
            "# Progress so far\n\n"
            f"$ awawa status STEP {progress}\n"
            "STEP (1):\n"
            f"  @STEP.s1  (none)  {progress}:26  incoming 0\n\n"
            f"$ awawa status HANDOVER {progress}\n"
            "HANDOVER (0):\n\n"
            f"$ awawa show @STEP.s1 {progress}\n"
            "STEP s1\n"
            '\tDONE "read the task"\n'
            '\tNEXT "section 3"\n\n',
        )

    def test_should_open_the_next_brief_on_the_lint_output_and_the_file_whole_when_an_entry_fails_lint(self):
        # Arrange
        self.record("builder", HANDED_OVER_RESULT)
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n', document=None)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 20, completed.stderr)
        progress = self.runs / json.loads(completed.stdout)["run"] / "progress.awawa"
        opening, _, _ = (progress.parent / "segments" / "2" / "brief.md").read_text().partition("# Procedure deliver")
        self.assertEqual(
            opening,
            "# Progress so far\n\n"
            f"$ awawa lint --strict {progress}\n"
            f"{progress} — 1 error(s), 0 warning(s)\n"
            f"L014  error  {progress}:26:1\n"
            "      line does not start with a keyword ([A-Z][A-Z0-9_]*)\n\n"
            f"Rewrite {progress} so that awawa lint --strict {progress} passes, keeping every entry."
            " The file as it is:\n\n"
            f"{PROGRESS_SCHEMA}\nstep 1 done\n\n",
        )

    def test_should_relaunch_as_many_times_when_an_entry_fails_lint(self):
        # Arrange
        self.record("builder", HANDED_OVER_RESULT)
        self.configure_fake(COUNTING_CLIENT + 'progress = "step 1 done"\n', document=None)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 20, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 3)

    def test_should_not_relaunch_a_segment_on_a_progress_holding_its_schema_alone(self):
        # Arrange
        self.record("builder", HANDED_OVER_RESULT)
        self.configure_fake(COUNTING_CLIENT, document=None)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 20, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["segments"], 1)

    def test_should_ask_a_role_with_shell_to_format_and_lint_the_progress_after_each_append(self):
        # Arrange
        self.record("builder", DONE_RESULT)
        self.configure_fake(COUNTING_CLIENT, document=None)

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        progress = self.runs / RUN_ID / "progress.awawa"
        _, _, section = (self.runs / RUN_ID / "segments" / "1" / "brief.md").read_text().partition("# Progress file")
        self.assertEqual(
            section.partition("# End of segment")[0],
            f"\n\nThe progress is the awawa corpus {progress}: after the schema it holds, append one entity per"
            " entry, of a type the schema declares, named by the initial of its type in lower case and its rank"
            " among the entities of that type in order of writing.\n\n"
            "- STEP: a step the run completed\n"
            "- HANDOVER: the state of a run that hands over\n\n"
            "- one entry per major step: what it did in one line, the facts it established, one line each and five"
            " at most, and the next step as the procedure names it, complete at the end\n"
            "- a fact is what the next segment needs and no command gives back\n"
            "- never command output, a diff, the course of the step, a restatement of the brief or a fact an earlier"
            " entry holds\n"
            "- a handover entry holds what remains, one line per step not done, and the next step\n\n"
            f"After each append, run awawa fmt {progress} then awawa lint --strict {progress}, naming the file and"
            " never its directory.\n\n",
        )

    def test_should_ask_no_format_nor_lint_of_a_run_without_shell(self):
        # Arrange
        self.record("builder", DONE_RESULT)
        self.configure_fake(COUNTING_CLIENT, document=None)
        self.procedure.write_text(
            "---\ncapabilities: read, write\nbudget: 75\n---\nDeliver the task the brief names.\n"
        )

        # Act
        completed = self.run_deliver()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        brief = (self.runs / RUN_ID / "segments" / "1" / "brief.md").read_text()
        self.assertNotIn("After each append", brief)


class BrigadeRunOfASlotTheSlotClientsTableBindsTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.record("reviewer", DONE_RESULT)

    def run_slot(self, slot: str):
        return self.run_brigade(
            "run",
            str(self.procedure),
            "--slot",
            slot,
            "--cwd",
            str(self.workspace),
            "--json",
            path_directories=(FINISHING_CLIENT,),
        )

    def test_should_run_the_bound_slot_on_its_client(self):
        # Arrange
        self.configure_fake(f'{COUNTING_CLIENT}[slot_clients]\nbuild = "finishing"\n')

        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["client"], "finishing")

    def test_should_run_a_slot_the_table_leaves_unbound_on_the_client_key(self):
        # Arrange
        self.configure_fake(f'{COUNTING_CLIENT}[slot_clients]\nbuild = "finishing"\n')

        # Act
        completed = self.run_slot("review")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["client"], "fake")

    def test_should_name_the_client_of_the_slot_in_the_record_of_the_run(self):
        # Arrange
        self.configure_fake(f'{COUNTING_CLIENT}[slot_clients]\nbuild = "finishing"\n')

        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_run_record(json.loads(completed.stdout)["run"])["client"], "finishing")

    def test_should_name_the_client_of_the_slot_in_the_finished_run_of_the_ledger(self):
        # Arrange
        self.configure_fake(f'{COUNTING_CLIENT}[slot_clients]\nbuild = "finishing"\n')

        # Act
        completed = self.run_slot("build")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        [finished] = self.read_events("run.finished")
        self.assertEqual(finished["client"], "finishing")

    def test_should_exit_1_naming_the_key_and_the_file_of_a_table_off_its_shape(self):
        # Arrange
        rows = [
            (
                "a slot outside the nine",
                "",
                '[slot_clients]\ndeploy = "finishing"\n',
                "unknown key slot_clients.deploy",
            ),
            (
                "a value that is no string",
                "",
                "[slot_clients]\nbuild = 1\n",
                "slot_clients.build is an integer, not a string,",
            ),
            ("a key that is no table", 'slot_clients = "finishing"\n', "", "slot_clients is a string, not a table,"),
        ]
        for case, keys, table, expected_error in rows:
            with self.subTest(case=case):
                configuration = self.machine.corpus / "config.toml"
                self.configure_fake(f"{COUNTING_CLIENT}{table}", keys=keys)

                # Act
                completed = self.run_slot("build")

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, f"brigade run: {expected_error} in {configuration}\n")


RUN_DIRECTORY_CLAUDE = Path(__file__).resolve().parent / "fixtures" / "executables" / "claude-run-directory"


class BrigadeRunExportingItsDirectoryTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration('client = "claude-code"\ndocument = "markdown"\n')
        self.environment_record = Path(self.root.name) / "environment.txt"

    def test_should_hand_the_client_the_directory_of_the_run(self):
        # Act
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "run",
            str(self.procedure),
            "--slot",
            "build",
            "--cwd",
            str(self.workspace),
            environment={
                **self.machine.describe_environment(),
                "PATH": os.pathsep.join([str(RUN_DIRECTORY_CLAUDE), self.machine.search_path]),
                "BRIGADE_ENVIRONMENT_RECORD": str(self.environment_record),
            },
        )

        # Assert
        [run_directory] = self.runs.iterdir()
        self.assertEqual(self.environment_record.read_text(), f"{run_directory}\n", completed.stderr)
