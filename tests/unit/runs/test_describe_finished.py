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

ROOT = Path("/state/brigade")
NO_ARGUMENTS = {}
NO_WARNINGS = ()
NOT_IN_A_WAVE = "not launched by a wave"


def _create_plan(counts_steps: bool = True) -> RunPlan:
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
                )

                # Act
                finished = describe_finished(_create_plan(counts_steps=counts_steps), record)

                # Assert
                self.assertEqual(finished.nulls["main_steps"], reason)
