import unittest
from pathlib import Path

from brigade.ledger.run_finished import RunFinished
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.count_session_steps import SessionSteps
from brigade.runs.describe_finished import describe_finished
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.runs.run_result import RunResult
from brigade.runs.run_segment import SegmentRecord
from brigade.system.read_configuration import Configuration
from brigade.system.token_usage import TokenUsage

ROOT = Path("/state/brigade")
NO_ARGUMENTS = {}
NO_WARNINGS = ()
NOT_IN_A_WAVE = "not launched by a wave"
CUT = "cut at the wall-time limit"
STOPPED = "stopped by a signal"


def _create_plan(*, counts_steps: bool = True) -> RunPlan:
    return RunPlan(
        run_id="20261007T101817Z-2ee96f",
        run_directory=ROOT / "runs" / "20261007T101817Z-2ee96f",
        procedure=Procedure(
            name="awawa-task",
            location="built-in",
            argument="awawa-task",
            capabilities=("read", "write", "shell"),
            budget=75,
            body="Deliver the task.",
        ),
        slot="build",
        role=ResolvedRole(slot="build", role="ada", source="machine", front_matter={"reasoning": "standard"}, body=""),
        client="claude-code",
        client_adapter=None,
        document=None,
        progress_file=Path("/state/runs/r1/progress.md"),
        configuration=Configuration(),
        project="brigade",
        cwd=Path("/srv/brigade"),
        worktree=Path("/srv/brigade/.claude/worktrees/b71"),
        disposable_worktree=False,
        capabilities=("read", "write", "shell"),
        wall_limit_s=2820.0,
        arguments=NO_ARGUMENTS,
        brief_path=None,
        brief=None,
        counts_steps=counts_steps,
        reads_actions=True,
        reads_transcripts=True,
        handovers=1,
        warnings=NO_WARNINGS,
    )


def _create_result(steps: int | None) -> RunResult:
    return RunResult(
        outcome="done",
        steps=steps,
        usage=None,
        session_id="857d4221",
        duration_ms=19091,
        error_class=None,
        reset=None,
        message=None,
    )


class DescribeFinishedTest(unittest.TestCase):
    def test_should_record_the_steps_counted_from_the_transcripts_the_measured_duration_and_the_cost(self):
        # Arrange
        record = SegmentRecord(
            number=1,
            result=_create_result(steps=None),
            exit_code=0,
            measured_ms=900000,
            cost_usd=3.63,
            counted_steps=SessionSteps(main_steps=42, total_steps=54),
            uncounted=None,
            adapter_failure=None,
        )

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(
            finished,
            RunFinished(
                run="20261007T101817Z-2ee96f",
                segment=1,
                procedure="awawa-task",
                slot="build",
                role="ada",
                client="claude-code",
                project="brigade",
                session="857d4221",
                main_steps=42,
                total_steps=54,
                duration_ms=900000,
                usage=None,
                outcome="done",
                error_class=None,
                exit=0,
                wave=None,
                task=None,
                nulls={
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "usage": "the client reported no usage",
                    "error_class": "the run did not fail",
                },
                cost_usd=3.63,
            ),
        )

    def test_should_fall_back_on_the_steps_the_client_reported_when_the_transcripts_are_uncounted(self):
        # Arrange
        record = SegmentRecord(
            number=1,
            result=_create_result(steps=52),
            exit_code=0,
            measured_ms=900000,
            cost_usd=None,
            counted_steps=None,
            uncounted="the client reads no transcript",
            adapter_failure=None,
        )

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(finished.main_steps, 52)
        self.assertIsNone(finished.total_steps)
        self.assertEqual(finished.nulls["total_steps"], "the client reads no transcript")

    def test_should_name_both_reasons_of_main_steps_left_unknown(self):
        for counts_steps, uncounted, reason in [
            (
                True,
                "the transcript could not be read: unreadable transcript at /home/ada/857d4221.jsonl: 'message'",
                (
                    "the client reported no step count and the transcript could not be read:"
                    " unreadable transcript at /home/ada/857d4221.jsonl: 'message'"
                ),
            ),
            (
                True,
                "the client reported no session",
                "the client reported no step count and the client reported no session",
            ),
            (False, "the client reads no transcript", "the client counts no steps and the client reads no transcript"),
        ]:
            with self.subTest(counts_steps=counts_steps, uncounted=uncounted):
                # Arrange
                record = SegmentRecord(
                    number=1,
                    result=_create_result(steps=None),
                    exit_code=0,
                    measured_ms=900000,
                    cost_usd=None,
                    counted_steps=None,
                    uncounted=uncounted,
                    adapter_failure=None,
                )

                # Act
                finished = describe_finished(_create_plan(counts_steps=counts_steps), record)

                # Assert
                self.assertEqual(finished.nulls["main_steps"], reason)


def _create_cut(session_id: str | None, usage: TokenUsage | None) -> RunResult:
    return RunResult(
        outcome="wall_limit",
        steps=None,
        usage=usage,
        session_id=session_id,
        duration_ms=2820000,
        error_class=None,
        reset=None,
        message="cut at the wall-time limit of 2820 s",
    )


class DescribeFinishedOfACutSegmentTest(unittest.TestCase):
    def test_should_record_the_session_the_steps_and_the_usage_measured_from_the_transcripts(self):
        # Arrange
        usage = TokenUsage(
            input_tokens=188, output_tokens=88524, cache_creation_input_tokens=240807, cache_read_input_tokens=16937660
        )
        record = SegmentRecord(
            number=1,
            result=_create_cut(session_id="a47607d0-5a3d-4910-8978-9aad5d0e7796", usage=usage),
            exit_code=None,
            measured_ms=2820000,
            cost_usd=None,
            counted_steps=SessionSteps(main_steps=106, total_steps=106),
            uncounted=None,
            adapter_failure=None,
        )

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(
            finished,
            RunFinished(
                run="20261007T101817Z-2ee96f",
                segment=1,
                procedure="awawa-task",
                slot="build",
                role="ada",
                client="claude-code",
                project="brigade",
                session="a47607d0-5a3d-4910-8978-9aad5d0e7796",
                main_steps=106,
                total_steps=106,
                duration_ms=2820000,
                usage=TokenUsage(
                    input_tokens=188,
                    output_tokens=88524,
                    cache_creation_input_tokens=240807,
                    cache_read_input_tokens=16937660,
                ),
                outcome="wall_limit",
                error_class=None,
                exit=None,
                wave=None,
                task=None,
                nulls={"wave": NOT_IN_A_WAVE, "task": NOT_IN_A_WAVE, "error_class": CUT, "exit": CUT},
                cost_usd=None,
            ),
        )

    def test_should_name_the_reason_a_cut_segment_is_left_unmeasured(self):
        # Arrange
        rows = [
            (
                "a client naming no session at launch",
                None,
                "the client names no session at launch",
                {
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "session": "the client names no session at launch",
                    "main_steps": "the client names no session at launch",
                    "total_steps": "the client names no session at launch",
                    "usage": "the client names no session at launch",
                    "error_class": CUT,
                    "exit": CUT,
                },
            ),
            (
                "a client naming no session at launch and reading no transcript",
                None,
                "the client reads no transcript",
                {
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "session": "the client names no session at launch",
                    "main_steps": "the client reads no transcript",
                    "total_steps": "the client reads no transcript",
                    "usage": "the client reads no transcript",
                    "error_class": CUT,
                    "exit": CUT,
                },
            ),
            (
                "a transcript that cannot be read",
                "a47607d0-5a3d-4910-8978-9aad5d0e7796",
                "the transcript could not be read: no transcript of session a47607d0",
                {
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "main_steps": "the transcript could not be read: no transcript of session a47607d0",
                    "total_steps": "the transcript could not be read: no transcript of session a47607d0",
                    "usage": "the transcript could not be read: no transcript of session a47607d0",
                    "error_class": CUT,
                    "exit": CUT,
                },
            ),
        ]
        for case, session_id, uncounted, expected_nulls in rows:
            with self.subTest(case):
                # Arrange
                record = SegmentRecord(
                    number=1,
                    result=_create_cut(session_id=session_id, usage=None),
                    exit_code=None,
                    measured_ms=2820000,
                    cost_usd=None,
                    counted_steps=None,
                    uncounted=uncounted,
                    adapter_failure=None,
                )

                # Act
                finished = describe_finished(_create_plan(), record)

                # Assert
                self.assertEqual(finished.nulls, expected_nulls)


class DescribeFinishedOfAStoppedSegmentTest(unittest.TestCase):
    def test_should_name_the_stop_and_the_reason_a_stopped_segment_is_left_unmeasured(self):
        # Arrange
        rows = [
            (
                "a client stopped while it ran, naming no session at launch",
                None,
                "the client names no session at launch",
                {
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "session": "the client names no session at launch",
                    "main_steps": "the client names no session at launch",
                    "total_steps": "the client names no session at launch",
                    "usage": "the client names no session at launch",
                    "error_class": STOPPED,
                    "exit": STOPPED,
                },
            ),
            (
                "a run stopped before its client was launched",
                "a47607d0-5a3d-4910-8978-9aad5d0e7796",
                "the client was never launched",
                {
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "main_steps": "the client was never launched",
                    "total_steps": "the client was never launched",
                    "usage": "the client was never launched",
                    "error_class": STOPPED,
                    "exit": STOPPED,
                },
            ),
        ]
        for case, session_id, uncounted, expected_nulls in rows:
            with self.subTest(case):
                # Arrange
                record = SegmentRecord(
                    number=1,
                    result=RunResult(
                        outcome="stopped",
                        steps=None,
                        usage=None,
                        session_id=session_id,
                        duration_ms=4000,
                        error_class=None,
                        reset=None,
                        message="stopped by a signal",
                    ),
                    exit_code=None,
                    measured_ms=4000,
                    cost_usd=None,
                    counted_steps=None,
                    uncounted=uncounted,
                    adapter_failure=None,
                )

                # Act
                finished = describe_finished(_create_plan(), record)

                # Assert
                self.assertEqual(finished.nulls, expected_nulls)


class DescribeFinishedOfASegmentWhoseAdapterFailedToLaunchItsClientTest(unittest.TestCase):
    def test_should_name_the_failure_of_the_adapter_and_the_client_never_launched(self):
        # Arrange
        record = SegmentRecord(
            number=1,
            result=RunResult(
                outcome="failed",
                steps=None,
                usage=None,
                session_id=None,
                duration_ms=0,
                error_class=None,
                reset=None,
                message="client adapter claude-code answered launch-argv: lacks the key argv",
            ),
            exit_code=None,
            measured_ms=0,
            cost_usd=None,
            counted_steps=None,
            uncounted="the client was never launched",
            adapter_failure="client adapter claude-code answered launch-argv: lacks the key argv",
        )

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(
            finished.nulls,
            {
                "wave": NOT_IN_A_WAVE,
                "task": NOT_IN_A_WAVE,
                "session": "the client names no session at launch",
                "main_steps": "the client was never launched",
                "total_steps": "the client was never launched",
                "usage": "the client was never launched",
                "error_class": "client adapter claude-code answered launch-argv: lacks the key argv",
                "exit": "client adapter claude-code answered launch-argv: lacks the key argv",
            },
        )


def _create_failure(session_id: str | None, usage: TokenUsage | None, message: str) -> RunResult:
    return RunResult(
        outcome="failed",
        steps=None,
        usage=usage,
        session_id=session_id,
        duration_ms=4200,
        error_class=None,
        reset=None,
        message=message,
    )


class DescribeFinishedOfASegmentWhoseAdapterFailedToParseTheResultOfItsClientTest(unittest.TestCase):
    def test_should_name_the_failure_of_the_adapter_and_keep_what_the_transcripts_measured(self):
        # Arrange
        parse_failure = "client adapter claude-code answered parse-result: lacks the key outcome"
        usage = TokenUsage(input_tokens=12, output_tokens=840, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        rows = [
            (
                "transcripts read",
                "a47607d0-5a3d-4910-8978-9aad5d0e7796",
                usage,
                SessionSteps(main_steps=3, total_steps=5),
                None,
                {"wave": NOT_IN_A_WAVE, "task": NOT_IN_A_WAVE, "error_class": parse_failure},
            ),
            (
                "no transcript read",
                "a47607d0-5a3d-4910-8978-9aad5d0e7796",
                None,
                None,
                "the client reads no transcript",
                {
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "main_steps": "the client reads no transcript",
                    "total_steps": "the client reads no transcript",
                    "usage": "the client reads no transcript",
                    "error_class": parse_failure,
                },
            ),
            (
                "no session named at launch",
                None,
                None,
                None,
                "the client names no session at launch",
                {
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_IN_A_WAVE,
                    "session": "the client names no session at launch",
                    "main_steps": "the client names no session at launch",
                    "total_steps": "the client names no session at launch",
                    "usage": "the client names no session at launch",
                    "error_class": parse_failure,
                },
            ),
        ]
        for case, session_id, measured_usage, counted_steps, uncounted, expected_nulls in rows:
            with self.subTest(case):
                # Arrange
                record = SegmentRecord(
                    number=1,
                    result=_create_failure(session_id=session_id, usage=measured_usage, message=parse_failure),
                    exit_code=0,
                    measured_ms=4200,
                    cost_usd=None,
                    counted_steps=counted_steps,
                    uncounted=uncounted,
                    adapter_failure=parse_failure,
                )

                # Act
                finished = describe_finished(_create_plan(), record)

                # Assert
                self.assertEqual(finished.nulls, expected_nulls)

    def test_should_explain_the_nulls_of_a_client_answering_failed_itself_by_what_the_client_reported(self):
        # Arrange
        record = SegmentRecord(
            number=1,
            result=_create_failure(session_id="a47607d0-5a3d-4910-8978-9aad5d0e7796", usage=None, message="API error"),
            exit_code=1,
            measured_ms=4200,
            cost_usd=None,
            counted_steps=None,
            uncounted="the client reads no transcript",
            adapter_failure=None,
        )

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(
            finished.nulls,
            {
                "wave": NOT_IN_A_WAVE,
                "task": NOT_IN_A_WAVE,
                "main_steps": "the client reported no step count and the client reads no transcript",
                "total_steps": "the client reads no transcript",
                "usage": "the client reported no usage",
                "error_class": "the client reported no error class",
            },
        )
