import dataclasses
import itertools
import json
import os
import signal
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import ANY

from brigade.adapters.documents import markdown
from brigade.errors import BrigadeError, CannotWrite
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.count_session_steps import SessionSteps
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.runs.run_segment import run_segment
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.system.process_trace import ProcessTrace
from brigade.system.stop_signal_receiver import StopRequested, StopSignalReceiver
from brigade.system.token_usage import TokenUsage
from brigade.system.trail_writer import TrailWriter
from tests.process_launcher import ProcessLauncher
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

FIRST_SEGMENT = 1
NO_ARGUMENTS = {}
NO_WAVE = None
NO_TASK = None
NO_BRIEF = None
NO_WARNINGS = ()
NO_HANDOVER = 0
LAUNCH_ANSWER = {
    "schema_version": 1,
    "argv": ["double-client", "--print"],
    "environment": {"DOUBLE_CLIENT_MODE": "unattended"},
    "stdin": "the brief of the run",
    "session_id": None,
}
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
LIMIT_ALREADY_REACHED_S = 0.0
PID_HELD_BY_NO_PROCESS = 2**31 - 1


TRANSCRIPTS_ANSWER = {
    "schema_version": 1,
    "messages": [
        {
            "role": "assistant",
            "timestamp": None,
            "content": [],
            "tool_calls": 2,
            "id": "msg_main",
            "usage": {
                "input_tokens": 1,
                "output_tokens": 10,
                "cache_creation_input_tokens": 100,
                "cache_read_input_tokens": 1000,
            },
        }
    ],
    "subagents": [
        {
            "messages": [
                {
                    "role": "assistant",
                    "timestamp": None,
                    "content": [],
                    "tool_calls": 1,
                    "id": "msg_sub",
                    "usage": {
                        "input_tokens": 2,
                        "output_tokens": 20,
                        "cache_creation_input_tokens": 200,
                        "cache_read_input_tokens": 2000,
                    },
                }
            ]
        }
    ],
}


class ClientDouble:
    def __init__(self):
        self.operations = []
        self.requests = {}

    def answer(self, operation: str, request: dict) -> dict:
        self.operations.append(operation)
        self.requests[operation] = request
        if operation == "launch-argv":
            return LAUNCH_ANSWER
        if operation == "actions":
            return {"schema_version": 1, "actions": [{"kind": "text", "summary": request["output"].strip()}]}
        if operation == "transcripts":
            return TRANSCRIPTS_ANSWER
        return {
            "schema_version": 1,
            "outcome": "done",
            "steps": 12,
            "usage": None,
            "session_id": "session-b73",
            "duration_ms": 4200,
            "cost_usd": 0.42,
            "error_class": None,
            "reset": None,
            "message": request["stdout"],
        }


class ClientRefusingToReadTranscriptsDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "transcripts":
            raise BrigadeError("no transcript of session session-b73")
        return super().answer(operation, request)


class ClientReportingNoSessionDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "parse-result":
            return {**super().answer(operation, request), "session_id": None}
        return super().answer(operation, request)


class ClientAnsweringItsSessionDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "launch-argv":
            return {**super().answer(operation, request), "session_id": request["session_id"]}
        return super().answer(operation, request)


class ClientAnsweringItsSessionAndReportingNoneDouble(ClientAnsweringItsSessionDouble, ClientReportingNoSessionDouble):
    pass


class ClientAnsweringItsSessionAndRefusingToReadTranscriptsDouble(
    ClientAnsweringItsSessionDouble, ClientRefusingToReadTranscriptsDouble
):
    pass


class ClientStoppedAtTheSoftLimitDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "parse-result":
            return {**super().answer(operation, request), "outcome": "soft_limit", "message": None}
        return super().answer(operation, request)


class ClientRefusingToReadActionsDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "actions":
            return {"schema_version": 1}
        return super().answer(operation, request)


class ClientReadingNoActionsDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "actions":
            return {"schema_version": 1, "actions": []}
        return super().answer(operation, request)


class ClientAnsweringLaunchArgvWithoutSessionDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "launch-argv":
            return {
                "schema_version": 1,
                "argv": ["double-client", "--print"],
                "environment": {},
                "stdin": "the brief of the run",
            }
        return super().answer(operation, request)


class ClientAnsweringParseResultWithoutOutcomeDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "parse-result":
            return {
                "schema_version": 1,
                "steps": 12,
                "usage": None,
                "session_id": "session-b73",
                "duration_ms": 4200,
                "cost_usd": 0.42,
                "error_class": None,
                "reset": None,
                "message": None,
            }
        return super().answer(operation, request)


class ClientAnsweringItsSessionAndParseResultWithoutOutcomeDouble(
    ClientAnsweringItsSessionDouble, ClientAnsweringParseResultWithoutOutcomeDouble
):
    pass


class DocumentDescribingWithoutTextDouble:
    def describe_document(self, request: dict, runtime) -> dict:
        return {"schema_version": 1}


class ClockDouble:
    def __init__(self):
        self.now_s = 1000.0

    def read(self) -> float:
        return self.now_s


class ProcessExitingAfterAWhileDouble:
    pid = 4242

    def __init__(self, clock: ClockDouble, running_s: float):
        self._clock = clock
        self._running_s = running_s

    def wait(self, **_limit) -> int:
        self._clock.now_s += self._running_s
        return 0


class SpawnRunningAWhileDouble:
    def __init__(self, clock: ClockDouble, running_s: float):
        self._clock = clock
        self._running_s = running_s

    def spawn(self, request):
        request.stdout.write_text("the client finished the task", encoding="utf-8")
        request.stderr.write_text("", encoding="utf-8")
        return ProcessExitingAfterAWhileDouble(self._clock, self._running_s)


class ExitedProcessDouble:
    pid = 4242

    def wait(self, **_limit) -> int:
        return 0


class ProcessEndingItsLineAfterAPollDouble:
    pid = 4242

    def __init__(self, stdout: Path):
        self._stdout = stdout
        self._answers = [self._keep_running, self._end_the_line]

    def wait(self, timeout: float) -> int:
        return self._answers.pop(0)(timeout)

    def _keep_running(self, timeout: float) -> int:
        raise subprocess.TimeoutExpired("double-client", timeout)

    def _end_the_line(self, _timeout: float) -> int:
        with self._stdout.open("a", encoding="utf-8") as stream:
            stream.write("ng the test\n")
        return 0


class SpawnStoppingMidLineDouble:
    def spawn(self, request):
        request.stdout.write_text("Reading the task\nWriti", encoding="utf-8")
        request.stderr.write_text("", encoding="utf-8")
        return ProcessEndingItsLineAfterAPollDouble(request.stdout)


class SpawnDouble:
    def __init__(self, output: str = "the client finished the task"):
        self.requests = []
        self.output = output

    def spawn(self, request):
        self.requests.append(request)
        request.stdout.write_text(self.output, encoding="utf-8")
        request.stderr.write_text("", encoding="utf-8")
        return ExitedProcessDouble()


class ProcessStoppedAtTheLimitDouble:
    pid = PID_HELD_BY_NO_PROCESS

    def wait(self, timeout: float) -> int:
        return -signal.SIGTERM


class SpawnOutlivingTheLimitDouble:
    def spawn(self, request):
        request.stdout.write_text("Reading the task\n", encoding="utf-8")
        request.stderr.write_text("", encoding="utf-8")
        return ProcessStoppedAtTheLimitDouble()


LAUNCH_INSTANT = datetime(2026, 10, 7, 9, 5, 0, tzinfo=UTC)


def _read_journal_records(journal: Path) -> list[dict]:
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]


def _create_runtime(root: Path, spawn) -> Runtime:
    return create_test_runtime(create_test_paths(root), spawn_process=spawn.spawn, now=LAUNCH_INSTANT)


def _create_plan(
    root: Path,
    *,
    reads_actions: bool = False,
    client_type: type = ClientDouble,
    reads_transcripts: bool = False,
    wall_limit_s: float = 1500.0,
) -> RunPlan:
    return RunPlan(
        run_id="20261007T090000Z-b73a01",
        run_directory=root / "state" / "runs" / "20261007T090000Z-b73a01",
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
        client_adapter=client_type(),
        document=markdown,
        progress_file=root / "state" / "runs" / "20261007T090000Z-b73a01" / "progress.md",
        configuration=Configuration(),
        project=None,
        cwd=root / "project",
        worktree=root / "project",
        disposable_worktree=False,
        capabilities=("read", "write"),
        wall_limit_s=wall_limit_s,
        arguments=NO_ARGUMENTS,
        wave=NO_WAVE,
        task=NO_TASK,
        brief_path=None,
        brief=NO_BRIEF,
        counts_steps=True,
        reads_actions=reads_actions,
        reads_transcripts=reads_transcripts,
        handovers=NO_HANDOVER,
        warnings=NO_WARNINGS,
    )


class RunSegmentTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.spawn = SpawnDouble()

    def test_should_spawn_in_the_worktree_the_command_the_client_answers(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn), StopSignalReceiver())

        # Assert
        [request] = self.spawn.requests
        run_directory = str(self.root / "state" / "runs" / "20261007T090000Z-b73a01")
        self.assertEqual(request.argv, ("double-client", "--print"))
        self.assertEqual(request.cwd, str(self.root / "project"))
        self.assertEqual(
            request.environment,
            {
                "DOUBLE_CLIENT_MODE": "unattended",
                "BRIGADE_PROGRESS_FILE": f"{run_directory}/progress.md",
                "BRIGADE_RUN_DIR": run_directory,
            },
        )
        self.assertEqual(request.stdin, "the brief of the run")

    def test_should_refuse_a_description_of_the_progress_breaking_its_shape(self):
        # Arrange
        plan = dataclasses.replace(_create_plan(self.root), document=DocumentDescribingWithoutTextDouble())

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn), StopSignalReceiver())

        # Assert
        self.assertEqual(str(refusal.exception), "document plugin awawa answered describe_document: lacks the key text")

    def test_should_return_the_result_the_client_parses_from_what_the_process_wrote(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn), StopSignalReceiver())

        # Assert
        self.assertEqual(record.number, 1)
        self.assertEqual(record.exit_code, 0)
        self.assertEqual(record.outcome, "done")
        self.assertEqual(record.client_steps, 12)
        self.assertEqual(record.usage, None)
        self.assertEqual(record.session_id, "session-b73")
        self.assertEqual(record.error_class, None)
        self.assertEqual(record.reset, None)
        self.assertEqual(record.message, "the client finished the task")


class RunSegmentStepsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_count_the_steps_of_the_session_from_the_transcripts_the_client_reads(self):
        # Arrange
        plan = _create_plan(self.root, reads_transcripts=True)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(record.counted_steps, SessionSteps(main_steps=3, total_steps=5))

    def test_should_leave_the_steps_uncounted_with_their_reason(self):
        # Arrange
        rows = [
            (ClientDouble, False, "the client reads no transcript"),
            (
                ClientRefusingToReadTranscriptsDouble,
                True,
                "the transcript could not be read: no transcript of session session-b73",
            ),
            (ClientReportingNoSessionDouble, True, "the client reported no session"),
        ]
        for client_type, reads_transcripts, expected_reason in rows:
            with self.subTest(client=client_type.__name__):
                # Arrange
                plan = _create_plan(self.root, client_type=client_type, reads_transcripts=reads_transcripts)

                # Act
                record = run_segment(
                    plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver()
                )

                # Assert
                self.assertIsNone(record.counted_steps)
                self.assertEqual(record.uncounted, expected_reason)

    def test_should_keep_the_cost_the_client_reports(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(record.cost_usd, 0.42)


class RunSegmentSoftLimitTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_carry_the_soft_limit_read_on_the_clock_at_launch_in_the_launch_request(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(plan.client_adapter.requests["launch-argv"]["stop_at"], "2026-10-07T09:28:00Z")

    def test_should_carry_no_soft_limit_for_a_wall_time_limit_not_above_the_margin(self):
        # Arrange
        plan = _create_plan(self.root, wall_limit_s=120.0)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertIsNone(plan.client_adapter.requests["launch-argv"]["stop_at"])

    def test_should_record_a_segment_its_client_stopped_at_the_soft_limit_as_one_ended_done(self):
        # Arrange
        plan = _create_plan(self.root, client_type=ClientStoppedAtTheSoftLimitDouble)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(record.outcome, "soft_limit")
        self.assertEqual(record.client_steps, 12)
        self.assertEqual(record.session_id, "session-b73")
        self.assertEqual(record.message, None)
        self.assertEqual(record.exit_code, 0)
        self.assertEqual(record.cost_usd, 0.42)


class RunSegmentSessionTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_name_a_new_session_in_the_launch_request(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertRegex(plan.client_adapter.requests["launch-argv"]["session_id"], UUID_PATTERN)

    def test_should_keep_the_session_the_client_reports_in_its_result(self):
        # Arrange
        plan = _create_plan(self.root, client_type=ClientAnsweringItsSessionDouble)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(record.session_id, "session-b73")

    def test_should_take_the_session_named_at_launch_when_the_result_reports_none(self):
        # Arrange
        plan = _create_plan(
            self.root, client_type=ClientAnsweringItsSessionAndReportingNoneDouble, reads_transcripts=True
        )

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        launched_session = plan.client_adapter.requests["launch-argv"]["session_id"]
        self.assertEqual(record.session_id, launched_session)
        self.assertEqual(plan.client_adapter.requests["transcripts"]["session_id"], launched_session)


class RunSegmentCutAtTheWallTimeLimitTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.spawn = SpawnOutlivingTheLimitDouble()

    def test_should_measure_the_session_named_at_launch_from_its_transcripts(self):
        # Arrange
        plan = _create_plan(
            self.root,
            client_type=ClientAnsweringItsSessionDouble,
            reads_transcripts=True,
            wall_limit_s=LIMIT_ALREADY_REACHED_S,
        )

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn), StopSignalReceiver())

        # Assert
        launched_session = plan.client_adapter.requests["launch-argv"]["session_id"]
        self.assertEqual(plan.client_adapter.requests["transcripts"]["session_id"], launched_session)
        self.assertEqual(record.outcome, "wall_limit")
        self.assertEqual(record.session_id, launched_session)
        self.assertEqual(
            record.usage,
            TokenUsage(input_tokens=3, output_tokens=30, cache_creation_input_tokens=300, cache_read_input_tokens=3000),
        )
        self.assertEqual(record.counted_steps, SessionSteps(main_steps=3, total_steps=5))
        self.assertIsNone(record.uncounted)
        self.assertIsNone(record.cost_usd)

    def test_should_leave_a_cut_segment_unmeasured_with_its_reason(self):
        # Arrange
        rows = [
            (ClientDouble, True, "the client names no session at launch"),
            (ClientAnsweringItsSessionDouble, False, "the client reads no transcript"),
            (
                ClientAnsweringItsSessionAndRefusingToReadTranscriptsDouble,
                True,
                "the transcript could not be read: no transcript of session session-b73",
            ),
        ]
        for client_type, reads_transcripts, expected_reason in rows:
            with self.subTest(client=client_type.__name__):
                # Arrange
                plan = _create_plan(
                    self.root,
                    client_type=client_type,
                    reads_transcripts=reads_transcripts,
                    wall_limit_s=LIMIT_ALREADY_REACHED_S,
                )

                # Act
                record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn), StopSignalReceiver())

                # Assert
                self.assertIsNone(record.counted_steps)
                self.assertIsNone(record.usage)
                self.assertEqual(record.uncounted, expected_reason)


class RunSegmentJournalTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.journal = self.root / "state" / "runs" / "20261007T090000Z-b73a01" / "journal.jsonl"

    def test_should_journal_one_raw_record_per_line_of_a_client_that_reads_no_actions(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=False)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(
            json.loads(self.journal.read_text()),
            {
                "schema_version": 1,
                "at": "2026-10-07T09:05:00Z",
                "segment": 1,
                "kind": "raw",
                "summary": "the client finished the task",
                "cut": False,
            },
        )

    def test_should_journal_the_actions_the_client_reads_in_the_output(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=True)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(
            json.loads(self.journal.read_text()),
            {
                "schema_version": 1,
                "at": "2026-10-07T09:05:00Z",
                "segment": 1,
                "kind": "text",
                "summary": "the client finished the task",
                "cut": False,
            },
        )

    def test_should_ask_the_client_for_no_actions_when_the_segment_wrote_nothing(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=True)
        no_output = ""

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble(no_output)), StopSignalReceiver())

        # Assert
        self.assertEqual(plan.client_adapter.operations, ["launch-argv", "parse-result"])

    def test_should_journal_a_line_the_client_was_still_writing_once_it_is_whole(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=False)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnStoppingMidLineDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(
            _read_journal_records(self.journal),
            [
                {
                    "schema_version": 1,
                    "at": "2026-10-07T09:05:00Z",
                    "segment": 1,
                    "kind": "raw",
                    "summary": "Reading the task",
                    "cut": False,
                },
                {
                    "schema_version": 1,
                    "at": "2026-10-07T09:05:00Z",
                    "segment": 1,
                    "kind": "raw",
                    "summary": "Writing the test",
                    "cut": False,
                },
            ],
        )

    def test_should_name_the_journal_it_cannot_write(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=False)
        self.journal.mkdir(parents=True)

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.journal}: Is a directory")

    def test_should_journal_nothing_of_an_output_in_which_the_client_reads_no_action(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=True, client_type=ClientReadingNoActionsDouble)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertFalse(self.journal.exists())

    def test_should_journal_raw_records_of_an_output_whose_actions_the_client_fails_to_read(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=True, client_type=ClientRefusingToReadActionsDouble)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(
            json.loads(self.journal.read_text()),
            {
                "schema_version": 1,
                "at": "2026-10-07T09:05:00Z",
                "segment": 1,
                "kind": "raw",
                "summary": "the client finished the task",
                "cut": False,
            },
        )


class StopRequestedBeforeTheSpawnDouble:
    requested = True

    def raising(self):
        raise AssertionError("run_segment waited for a client it should not have spawned")


class StopArrivingAfterTheSpawnDouble:
    requested = False

    def raising(self):
        return self

    def __enter__(self):
        raise StopRequested

    def __exit__(self, *_exception):
        return False


class ClientStoppedWhileReadingActionsDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "actions":
            os.kill(os.getpid(), signal.SIGTERM)
        return super().answer(operation, request)


class ProcessRunningPastAPollDouble:
    pid = PID_HELD_BY_NO_PROCESS

    def __init__(self):
        self._answers = itertools.chain([self._keep_running], itertools.repeat(self._end_stopped))

    def wait(self, timeout: float) -> int:
        return next(self._answers)(timeout)

    def _keep_running(self, timeout: float) -> int:
        raise subprocess.TimeoutExpired("double-client", timeout)

    def _end_stopped(self, _timeout: float) -> int:
        return -signal.SIGTERM


class SpawnRunningPastAPollDouble:
    def spawn(self, request):
        request.stdout.write_text("Reading the task\n", encoding="utf-8")
        request.stderr.write_text("", encoding="utf-8")
        return ProcessRunningPastAPollDouble()


class SpawnSleepingClientDouble:
    def __init__(self, test: unittest.TestCase):
        self.test = test
        self.process = None

    def spawn(self, request):
        request.stdout.write_text("Reading the task\n", encoding="utf-8")
        request.stderr.write_text("", encoding="utf-8")
        self.process = ProcessLauncher.start(["sleep", "5"], start_new_session=True)
        self.test.addCleanup(self.process.wait)
        self.test.addCleanup(self.process.kill)
        return self.process


class RunSegmentStoppedBeforeItsClientIsSpawnedTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_end_the_segment_stopped_without_spawning_the_client(self):
        # Arrange
        spawn = SpawnDouble()

        # Act
        record = run_segment(
            _create_plan(self.root),
            FIRST_SEGMENT,
            _create_runtime(self.root, spawn),
            StopRequestedBeforeTheSpawnDouble(),
        )

        # Assert
        self.assertEqual(spawn.requests, [])
        self.assertEqual(record.outcome, "stopped")
        self.assertEqual(record.exit_code, None)
        self.assertEqual(record.uncounted, "the client was never launched")


class RunSegmentStoppedWhileItsClientRunsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.spawn = SpawnSleepingClientDouble(self)

    def test_should_stop_the_group_of_the_client_and_end_the_segment_stopped(self):
        # Act
        record = run_segment(
            _create_plan(self.root),
            FIRST_SEGMENT,
            _create_runtime(self.root, self.spawn),
            StopArrivingAfterTheSpawnDouble(),
        )

        # Assert
        self.assertEqual(self.spawn.process.returncode, -signal.SIGTERM)
        self.assertEqual(record.outcome, "stopped")
        self.assertEqual(record.exit_code, None)
        self.assertEqual(record.message, "stopped by a signal")

    def test_should_record_the_client_stopped_in_the_trail(self):
        # Arrange
        traces = []
        runtime = dataclasses.replace(_create_runtime(self.root, self.spawn), trail=TrailWriter(traces.append))

        # Act
        run_segment(_create_plan(self.root), FIRST_SEGMENT, runtime, StopArrivingAfterTheSpawnDouble())

        # Assert
        self.assertEqual(
            traces,
            [ProcessTrace(("double-client", "--print"), str(self.root / "project"), "stopped", None, ANY)],
        )

    def test_should_measure_the_session_named_at_launch_from_its_transcripts(self):
        # Arrange
        plan = _create_plan(self.root, client_type=ClientAnsweringItsSessionDouble, reads_transcripts=True)

        # Act
        record = run_segment(
            plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn), StopArrivingAfterTheSpawnDouble()
        )

        # Assert
        self.assertEqual(record.session_id, plan.client_adapter.requests["launch-argv"]["session_id"])
        self.assertEqual(record.counted_steps, SessionSteps(main_steps=3, total_steps=5))


class RunSegmentStoppedWhileItsJournalIsWrittenTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.journal = self.root / "state" / "runs" / "20261007T090000Z-b73a01" / "journal.jsonl"

    def test_should_keep_in_the_journal_the_lines_the_stop_arrived_on(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=True, client_type=ClientStoppedWhileReadingActionsDouble)

        # Act
        with StopSignalReceiver() as stop:
            run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnRunningPastAPollDouble()), stop)

        # Assert
        self.assertEqual(
            _read_journal_records(self.journal),
            [
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "text",
                    "summary": "Reading the task",
                    "cut": False,
                }
            ],
        )


class RunSegmentOfAnAdapterAnsweringOutsideItsContractTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_end_the_segment_failed_naming_the_adapter_the_operation_and_the_problem(self):
        # Arrange
        rows = [
            (
                ClientAnsweringLaunchArgvWithoutSessionDouble,
                "client adapter double-client answered launch-argv: lacks the key session_id",
            ),
            (
                ClientAnsweringParseResultWithoutOutcomeDouble,
                "client adapter double-client answered parse-result: lacks the key outcome",
            ),
        ]
        for client_type, expected_message in rows:
            with self.subTest(client=client_type.__name__):
                # Arrange
                plan = _create_plan(self.root, client_type=client_type)

                # Act
                record = run_segment(
                    plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver()
                )

                # Assert
                self.assertEqual(record.outcome, "failed")
                self.assertEqual(record.client_steps, None)
                self.assertEqual(record.usage, None)
                self.assertEqual(record.session_id, None)
                self.assertEqual(record.error_class, None)
                self.assertEqual(record.reset, None)
                self.assertEqual(record.message, expected_message)

    def test_should_record_the_failure_of_the_adapter_apart_from_the_result_of_the_client(self):
        # Arrange
        rows = [
            (
                ClientAnsweringLaunchArgvWithoutSessionDouble,
                "client adapter double-client answered launch-argv: lacks the key session_id",
            ),
            (
                ClientAnsweringParseResultWithoutOutcomeDouble,
                "client adapter double-client answered parse-result: lacks the key outcome",
            ),
        ]
        for client_type, expected_failure in rows:
            with self.subTest(client=client_type.__name__):
                # Arrange
                plan = _create_plan(self.root, client_type=client_type)

                # Act
                record = run_segment(
                    plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver()
                )

                # Assert
                self.assertEqual(record.adapter_failure, expected_failure)

    def test_should_keep_the_exit_code_of_the_client_whose_result_the_adapter_failed_to_parse(self):
        # Arrange
        plan = _create_plan(self.root, client_type=ClientAnsweringParseResultWithoutOutcomeDouble)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(record.exit_code, 0)

    def test_should_end_the_segment_failed_without_spawning_the_client_whose_launch_the_adapter_failed_to_give(self):
        # Arrange
        spawn = SpawnDouble()
        plan = _create_plan(self.root, client_type=ClientAnsweringLaunchArgvWithoutSessionDouble)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, spawn), StopSignalReceiver())

        # Assert
        self.assertEqual(spawn.requests, [])
        self.assertEqual(record.outcome, "failed")
        self.assertEqual(record.exit_code, None)
        self.assertEqual(record.uncounted, "the client was never launched")

    def test_should_measure_the_session_named_at_launch_from_its_transcripts(self):
        # Arrange
        plan = _create_plan(
            self.root, client_type=ClientAnsweringItsSessionAndParseResultWithoutOutcomeDouble, reads_transcripts=True
        )

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()), StopSignalReceiver())

        # Assert
        self.assertEqual(record.session_id, plan.client_adapter.requests["launch-argv"]["session_id"])
        self.assertEqual(record.counted_steps, SessionSteps(main_steps=3, total_steps=5))

    def test_should_keep_the_time_measured_until_the_client_exited(self):
        # Arrange
        clock = ClockDouble()
        plan = _create_plan(self.root, client_type=ClientAnsweringParseResultWithoutOutcomeDouble)
        runtime = dataclasses.replace(
            _create_runtime(self.root, SpawnRunningAWhileDouble(clock, running_s=4.2)), read_monotonic=clock.read
        )

        # Act
        record = run_segment(plan, FIRST_SEGMENT, runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(record.measured_ms, 4200)
