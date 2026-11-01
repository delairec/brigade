import json
import os
import signal
import sys
from pathlib import Path

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, RunTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.value_matchers import DurationUnderMatcher, PatternMatcher

SHA256_DIGEST = PatternMatcher("^[0-9a-f]{64}$")
NO_EDIT_TOOL_NAMED = {
    "steps_to_first_edit": "the client names no edit tool",
    "tokens_to_first_edit": "the client names no edit tool",
}

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"
INSTANT_PATTERN = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"
NOT_IN_A_WAVE = "not launched by a wave"
NOT_FOR_A_TASK = "not launched for a task"
CUT = "cut at the wall-time limit"
STOPPED = "stopped by a signal"
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
QUICK_PROCEDURE = "---\ncapabilities: read, write, shell\n---\nAnswer at once.\n"


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


class BrigadeRunOfAProcedureGivenByNameTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.instructions = Path(self.root.name) / "instructions"
        (self.instructions / "procedures").mkdir(parents=True)
        self.configure_fake(COUNTING_CLIENT, keys=f'instructions = "{self.instructions}"\n')
        self.record("builder", DONE_RESULT)

    def test_should_exit_1_naming_a_procedure_that_resolves_nowhere(self):
        # Act
        completed = self.run_brigade("run", "missing", "--slot", "build", "--cwd", str(self.workspace))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade run: no procedure missing: not shipped with brigade and not in {self.instructions}/procedures\n",
        )


class BrigadeRunOfARequestItCannotPlanTest(RunTestCase):
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
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": PatternMatcher(INSTANT_PATTERN),
                    "event": "run.finished",
                    "run": run_id,
                    "segment": 1,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": "fake-session",
                    "main_steps": 12,
                    "total_steps": None,
                    "duration_ms": DurationUnderMatcher(10000),
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
                    "role_digest": SHA256_DIGEST,
                    "procedure_digest": SHA256_DIGEST,
                    "shipped_budget": 75,
                    "nulls": {
                        **NO_EDIT_TOOL_NAMED,
                        "project": "no project given",
                        "wave": NOT_IN_A_WAVE,
                        "task": NOT_FOR_A_TASK,
                        "total_steps": "the client reads no transcript",
                        "error_class": "the run did not fail",
                    },
                    "cost_usd": 0.42,
                }
            ],
        )


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

    def terminate(self, brigade_pid: int) -> None:
        os.kill(brigade_pid, signal.SIGTERM)
        self.wait_for_exit(brigade_pid)

    def test_should_record_the_stop_in_the_finished_event_and_in_the_processes_of_the_run(self):
        # Arrange
        run_id = self.start_detached()
        brigade_pid = self.read_run_pid(run_id)
        self.wait_for_client(brigade_pid)

        # Act
        self.terminate(brigade_pid)

        # Assert
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": PatternMatcher(INSTANT_PATTERN),
                    "event": "run.finished",
                    "run": run_id,
                    "segment": 1,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": PatternMatcher(UUID_PATTERN),
                    "main_steps": None,
                    "total_steps": None,
                    "duration_ms": DurationUnderMatcher(10000),
                    "usage": None,
                    "outcome": "stopped",
                    "error_class": None,
                    "exit": None,
                    "wave": None,
                    "task": None,
                    "role_digest": SHA256_DIGEST,
                    "procedure_digest": SHA256_DIGEST,
                    "shipped_budget": 75,
                    "nulls": {
                        **NO_EDIT_TOOL_NAMED,
                        "project": "no project given",
                        "wave": NOT_IN_A_WAVE,
                        "task": NOT_FOR_A_TASK,
                        "main_steps": "the client reads no transcript",
                        "total_steps": "the client reads no transcript",
                        "usage": "the client reads no transcript",
                        "error_class": STOPPED,
                        "exit": STOPPED,
                    },
                    "message": STOPPED,
                }
            ],
        )
        self.assertEqual(
            list(map(json.loads, (self.runs / run_id / "processes.jsonl").read_text().splitlines())),
            [
                {
                    "schema_version": 1,
                    "argv": [
                        sys.executable,
                        str(CLONE_ENTRY_POINT),
                        "run",
                        str(self.procedure),
                        "--slot",
                        "build",
                        "--cwd",
                        str(self.workspace),
                        "--run-id",
                        run_id,
                    ],
                    "cwd": str(self.workspace),
                    "exit": None,
                    "duration_ms": None,
                    "outcome": "spawned",
                    "pid": brigade_pid,
                },
                {
                    "schema_version": 1,
                    "argv": [
                        "sh",
                        "-c",
                        (
                            'while [ -n "$1" ] && [ -e "$1" ]; do sleep 0.05; done; until [ "$(date -u +%s)" -ge "$5" ];'
                            ' do sleep 0.1; done; if [ -n "$2" ]; then printf "%s\\n" "$2" >> "$BRIGADE_PROGRESS_FILE"; fi;'
                            ' while IFS= read -r line || [ -n "$line" ]; do printf "%s\\n" "$line"; sleep "$4"; done < "$3"'
                        ),
                        "fake",
                        str(self.hold),
                        "",
                        str(self.recordings / "builder.json"),
                        "0",
                        "0",
                    ],
                    "cwd": str(self.workspace),
                    "exit": None,
                    "duration_ms": DurationUnderMatcher(10000),
                    "outcome": "stopped",
                },
            ],
        )


class BrigadeRunOnTheClockTest(RunTestCase):
    def setUp(self):
        super().setUp()
        self.configure_fake(COUNTING_CLIENT + self.hold_the_client(), keys="seconds_per_step = 0.004\n")
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
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": PatternMatcher(INSTANT_PATTERN),
                    "event": "run.finished",
                    "run": json.loads(completed.stdout)["run"],
                    "segment": 1,
                    "procedure": "quick",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": PatternMatcher(UUID_PATTERN),
                    "main_steps": None,
                    "total_steps": None,
                    "duration_ms": DurationUnderMatcher(10000),
                    "usage": None,
                    "outcome": "wall_limit",
                    "error_class": None,
                    "exit": None,
                    "wave": None,
                    "task": None,
                    "role_digest": SHA256_DIGEST,
                    "procedure_digest": SHA256_DIGEST,
                    "shipped_budget": 75,
                    "nulls": {
                        **NO_EDIT_TOOL_NAMED,
                        "project": "no project given",
                        "wave": NOT_IN_A_WAVE,
                        "task": NOT_FOR_A_TASK,
                        "main_steps": "the client reads no transcript",
                        "total_steps": "the client reads no transcript",
                        "usage": "the client reads no transcript",
                        "error_class": CUT,
                        "exit": CUT,
                    },
                    "message": "cut at the wall-time limit of 0.376 s",
                },
                {
                    "schema_version": 1,
                    "ts": PatternMatcher(INSTANT_PATTERN),
                    "event": "signal.recorded",
                    "signal": "wall_limit_reached",
                    "project": None,
                    "procedure": "quick",
                    "run": json.loads(completed.stdout)["run"],
                    "segment": 1,
                    "budget": 75,
                    "wall_limit_s": 0.376,
                },
            ],
        )
