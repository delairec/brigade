import json
import signal
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import ANY

from brigade.errors import BrigadeError
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.count_session_steps import SessionSteps
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.runs.run_result import RunResult
from brigade.runs.run_segment import run_segment
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.read_configuration import Configuration
from brigade.system.token_usage import TokenUsage
from brigade.system.trail_writer import TrailWriter

FIRST_SEGMENT = 1
NO_PATH_NEEDED = ""
NO_ARGUMENTS = {}
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


class ClientRefusingToReadActionsDouble(ClientDouble):
    def answer(self, operation: str, request: dict) -> dict:
        if operation == "actions":
            return {"schema_version": 1}
        return super().answer(operation, request)


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


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"run_segment ran {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"run_segment resolved the {kind} plugin {name}")


def _read_journal_records(journal: Path) -> list[dict]:
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]


def _create_runtime(root: Path, spawn) -> Runtime:
    return Runtime(
        run_process=_refuse_process,
        spawn_process=spawn.spawn,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=NO_PATH_NEEDED,
        ),
        now=datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC),
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=_refuse_resolution,
    )


def _create_plan(
    root: Path,
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
        configuration=Configuration(),
        project=None,
        cwd=root / "project",
        worktree=root / "project",
        disposable_worktree=False,
        capabilities=("read", "write"),
        wall_limit_s=wall_limit_s,
        arguments=NO_ARGUMENTS,
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
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn))

        # Assert
        [request] = self.spawn.requests
        progress_file = str(self.root / "state" / "runs" / "20261007T090000Z-b73a01" / "progress.md")
        self.assertEqual(request.argv, ("double-client", "--print"))
        self.assertEqual(request.cwd, str(self.root / "project"))
        self.assertEqual(
            request.environment, {"DOUBLE_CLIENT_MODE": "unattended", "BRIGADE_PROGRESS_FILE": progress_file}
        )
        self.assertEqual(request.stdin, "the brief of the run")

    def test_should_return_the_result_the_client_parses_from_what_the_process_wrote(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn))

        # Assert
        self.assertEqual(record.number, 1)
        self.assertEqual(record.exit_code, 0)
        self.assertEqual(
            record.result,
            RunResult(
                outcome="done",
                steps=12,
                usage=None,
                session_id="session-b73",
                duration_ms=4200,
                error_class=None,
                reset=None,
                message="the client finished the task",
            ),
        )


class RunSegmentStepsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_count_the_steps_of_the_session_from_the_transcripts_the_client_reads(self):
        # Arrange
        plan = _create_plan(self.root, reads_transcripts=True)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
        self.assertEqual(record.counted_steps, SessionSteps(main_steps=3, total_steps=5))

    def test_should_leave_the_steps_uncounted_with_their_reason(self):
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
                record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

                # Assert
                self.assertIsNone(record.counted_steps)
                self.assertEqual(record.uncounted, expected_reason)

    def test_should_keep_the_cost_the_client_reports(self):
        # Arrange
        plan = _create_plan(self.root)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
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
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
        self.assertRegex(plan.client_adapter.requests["launch-argv"]["session_id"], UUID_PATTERN)

    def test_should_keep_the_session_the_client_reports_in_its_result(self):
        # Arrange
        plan = _create_plan(self.root, client_type=ClientAnsweringItsSessionDouble)

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
        self.assertEqual(record.result.session_id, "session-b73")

    def test_should_take_the_session_named_at_launch_when_the_result_reports_none(self):
        # Arrange
        plan = _create_plan(
            self.root, client_type=ClientAnsweringItsSessionAndReportingNoneDouble, reads_transcripts=True
        )

        # Act
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
        launched_session = plan.client_adapter.requests["launch-argv"]["session_id"]
        self.assertEqual(record.result.session_id, launched_session)
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
        record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn))

        # Assert
        launched_session = plan.client_adapter.requests["launch-argv"]["session_id"]
        self.assertEqual(plan.client_adapter.requests["transcripts"]["session_id"], launched_session)
        self.assertEqual(record.result.outcome, "wall_limit")
        self.assertEqual(record.result.session_id, launched_session)
        self.assertEqual(
            record.result.usage,
            TokenUsage(input_tokens=3, output_tokens=30, cache_creation_input_tokens=300, cache_read_input_tokens=3000),
        )
        self.assertEqual(record.counted_steps, SessionSteps(main_steps=3, total_steps=5))
        self.assertIsNone(record.uncounted)
        self.assertIsNone(record.cost_usd)

    def test_should_leave_a_cut_segment_unmeasured_with_its_reason(self):
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
                record = run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, self.spawn))

                # Assert
                self.assertIsNone(record.counted_steps)
                self.assertIsNone(record.result.usage)
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
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
        self.assertEqual(
            json.loads(self.journal.read_text()),
            {
                "schema_version": 1,
                "at": ANY,
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
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
        self.assertEqual(
            json.loads(self.journal.read_text()),
            {
                "schema_version": 1,
                "at": ANY,
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
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble(no_output)))

        # Assert
        self.assertEqual(plan.client_adapter.operations, ["launch-argv", "parse-result"])

    def test_should_journal_a_line_the_client_was_still_writing_once_it_is_whole(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=False)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnStoppingMidLineDouble()))

        # Assert
        self.assertEqual(
            _read_journal_records(self.journal),
            [
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "raw",
                    "summary": "Reading the task",
                    "cut": False,
                },
                {
                    "schema_version": 1,
                    "at": ANY,
                    "segment": 1,
                    "kind": "raw",
                    "summary": "Writing the test",
                    "cut": False,
                },
            ],
        )

    def test_should_journal_raw_records_of_an_output_whose_actions_the_client_fails_to_read(self):
        # Arrange
        plan = _create_plan(self.root, reads_actions=True, client_type=ClientRefusingToReadActionsDouble)

        # Act
        run_segment(plan, FIRST_SEGMENT, _create_runtime(self.root, SpawnDouble()))

        # Assert
        self.assertEqual(
            json.loads(self.journal.read_text()),
            {
                "schema_version": 1,
                "at": ANY,
                "segment": 1,
                "kind": "raw",
                "summary": "the client finished the task",
                "cut": False,
            },
        )
