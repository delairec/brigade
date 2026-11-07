import dataclasses
import unittest
from pathlib import Path

from brigade.ledger.run_finished import RunFinished
from brigade.roles.resolve_role import ResolvedRole
from brigade.runs.count_session_steps import SessionSteps
from brigade.runs.describe_finished import describe_finished
from brigade.runs.locate_first_edit import FirstEdit
from brigade.runs.plan_run import RunPlan
from brigade.runs.resolve_procedure import Procedure
from brigade.runs.run_segment import SegmentRecord
from brigade.system.parse_configuration import Configuration
from brigade.system.reset_hour import ResetHour
from brigade.system.token_usage import TokenUsage
from tests.unit.runs.create_run_plan import CAP_OF_FORTY_STEPS

ROOT = Path("/state/brigade")
NO_ARGUMENTS = {}
NO_WAVE = None
NO_TASK = None
NO_WARNINGS = ()
NOT_IN_A_WAVE = "not launched by a wave"
NOT_FOR_A_TASK = "not launched for a task"
CUT = "cut at the wall-time limit"
STOPPED = "stopped by a signal"
NO_EDIT_TOOL_NAMED = {
    "steps_to_first_edit": "the client names no edit tool",
    "tokens_to_first_edit": "the client names no edit tool",
}
EMPTY_ROLE_DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PROCEDURE_DIGEST = "e395b77e8ab7354e4418d2e1bb9d6f5c5b4de99c417c8b5ac1bc588d5d5c4151"


def _create_plan(*, counts_steps: bool = True, edit_tools: tuple[str, ...] = ()) -> RunPlan:
    return RunPlan(
        run_id="20261007T101817Z-2ee96f",
        run_directory=ROOT / "runs" / "20261007T101817Z-2ee96f",
        procedure=Procedure(
            name="awawa-task",
            location="built-in",
            argument="awawa-task",
            capabilities=("read", "write", "shell"),
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
        budget=CAP_OF_FORTY_STEPS,
        arguments=NO_ARGUMENTS,
        wave=NO_WAVE,
        task=NO_TASK,
        brief_path=None,
        brief=None,
        counts_steps=counts_steps,
        reads_actions=True,
        reads_transcripts=True,
        handovers=1,
        warnings=NO_WARNINGS,
        edit_tools=edit_tools,
    )


def _create_result(steps: int | None) -> dict:
    return {
        "outcome": "done",
        "client_steps": steps,
        "usage": None,
        "session_id": "857d4221",
        "error_class": None,
        "reset": None,
        "message": None,
    }


class DescribeFinishedTest(unittest.TestCase):
    def test_should_record_the_steps_counted_from_the_transcripts_the_measured_duration_and_the_cost(self):
        # Arrange
        record = SegmentRecord(
            number=1,
            **_create_result(steps=None),
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
                role_digest=EMPTY_ROLE_DIGEST,
                procedure_digest=PROCEDURE_DIGEST,
                shipped_budget=40,
                nulls={
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
            **_create_result(steps=52),
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
                    **_create_result(steps=None),
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


def _create_cut(session_id: str | None, usage: TokenUsage | None) -> dict:
    return {
        "outcome": "wall_limit",
        "client_steps": None,
        "usage": usage,
        "session_id": session_id,
        "error_class": None,
        "reset": None,
        "message": "cut at the wall-time limit of 2820 s",
    }


class DescribeFinishedOfACutSegmentTest(unittest.TestCase):
    def test_should_record_the_session_the_steps_and_the_usage_measured_from_the_transcripts(self):
        # Arrange
        usage = TokenUsage(
            input_tokens=188, output_tokens=88524, cache_creation_input_tokens=240807, cache_read_input_tokens=16937660
        )
        record = SegmentRecord(
            number=1,
            **_create_cut(session_id="a47607d0-5a3d-4910-8978-9aad5d0e7796", usage=usage),
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
                role_digest=EMPTY_ROLE_DIGEST,
                procedure_digest=PROCEDURE_DIGEST,
                shipped_budget=40,
                nulls={
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
                    "error_class": CUT,
                    "exit": CUT,
                },
                cost_usd=None,
                message="cut at the wall-time limit of 2820 s",
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
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
                    **_create_cut(session_id=session_id, usage=None),
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
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
                    outcome="stopped",
                    client_steps=None,
                    usage=None,
                    session_id=session_id,
                    error_class=None,
                    reset=None,
                    message="stopped by a signal",
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
            outcome="failed",
            client_steps=None,
            usage=None,
            session_id=None,
            error_class=None,
            reset=None,
            message="client adapter claude-code answered launch-argv: lacks the key argv",
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
                **NO_EDIT_TOOL_NAMED,
                "wave": NOT_IN_A_WAVE,
                "task": NOT_FOR_A_TASK,
                "session": "the client names no session at launch",
                "main_steps": "the client was never launched",
                "total_steps": "the client was never launched",
                "usage": "the client was never launched",
                "error_class": "client adapter claude-code answered launch-argv: lacks the key argv",
                "exit": "client adapter claude-code answered launch-argv: lacks the key argv",
            },
        )


def _create_failure(session_id: str | None, usage: TokenUsage | None, message: str) -> dict:
    return {
        "outcome": "failed",
        "client_steps": None,
        "usage": usage,
        "session_id": session_id,
        "error_class": None,
        "reset": None,
        "message": message,
    }


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
                {**NO_EDIT_TOOL_NAMED, "wave": NOT_IN_A_WAVE, "task": NOT_FOR_A_TASK, "error_class": parse_failure},
            ),
            (
                "no transcript read",
                "a47607d0-5a3d-4910-8978-9aad5d0e7796",
                None,
                None,
                "the client reads no transcript",
                {
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
                    **NO_EDIT_TOOL_NAMED,
                    "wave": NOT_IN_A_WAVE,
                    "task": NOT_FOR_A_TASK,
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
                    **_create_failure(session_id=session_id, usage=measured_usage, message=parse_failure),
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
            **_create_failure(session_id="a47607d0-5a3d-4910-8978-9aad5d0e7796", usage=None, message="API error"),
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
                **NO_EDIT_TOOL_NAMED,
                "wave": NOT_IN_A_WAVE,
                "task": NOT_FOR_A_TASK,
                "main_steps": "the client reported no step count and the client reads no transcript",
                "total_steps": "the client reads no transcript",
                "usage": "the client reported no usage",
                "error_class": "the client reported no error class",
            },
        )


class DescribeFinishedOfASegmentStoppedByAUsageLimitTest(unittest.TestCase):
    def test_should_keep_the_message_and_the_reset_hour_the_client_reported(self):
        # Arrange
        record = SegmentRecord(
            number=1,
            outcome="failed",
            session_id="ea3fca",
            client_steps=None,
            usage=None,
            error_class="rate_limit",
            reset=ResetHour(hour="23:30", timezone="Europe/Paris"),
            message="You've hit your session limit · resets 11:30pm",
            exit_code=1,
            measured_ms=4000,
            cost_usd=None,
            counted_steps=None,
            uncounted="the client reads no transcript",
            adapter_failure=None,
        )

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(finished.message, "You've hit your session limit · resets 11:30pm")
        self.assertEqual(finished.reset, ResetHour(hour="23:30", timezone="Europe/Paris"))


class DescribeFinishedOfARunOfNoProjectInAWaveTest(unittest.TestCase):
    def test_should_explain_the_missing_project_and_keep_the_wave_and_the_task(self):
        # Arrange
        plan = dataclasses.replace(_create_plan(), project=None, wave="w1", task="B1")
        record = SegmentRecord(
            number=1,
            **_create_result(steps=None),
            exit_code=0,
            measured_ms=900000,
            cost_usd=None,
            counted_steps=SessionSteps(main_steps=42, total_steps=54),
            uncounted=None,
            adapter_failure=None,
        )

        # Act
        finished = describe_finished(plan, record)

        # Assert
        self.assertEqual(finished.wave, "w1")
        self.assertEqual(finished.task, "B1")
        self.assertEqual(
            finished.nulls,
            {
                **NO_EDIT_TOOL_NAMED,
                "project": "no project given",
                "usage": "the client reported no usage",
                "error_class": "the run did not fail",
            },
        )


EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")
NO_EDIT_TOOL = ()


def _create_counted_record(*, counted_steps: SessionSteps | None, uncounted: str | None, first_edit: FirstEdit | None):
    return SegmentRecord(
        number=1,
        **_create_result(steps=None),
        exit_code=0,
        measured_ms=900000,
        cost_usd=None,
        counted_steps=counted_steps,
        uncounted=uncounted,
        adapter_failure=None,
        first_edit=first_edit,
    )


class DescribeFinishedFirstEditTest(unittest.TestCase):
    def test_should_record_the_step_and_the_tokens_of_the_first_edit(self):
        # Arrange
        record = _create_counted_record(
            counted_steps=SessionSteps(main_steps=42, total_steps=54),
            uncounted=None,
            first_edit=FirstEdit(steps=7, tokens=48000),
        )

        # Act
        finished = describe_finished(_create_plan(edit_tools=EDIT_TOOLS), record)

        # Assert
        self.assertEqual(finished.steps_to_first_edit, 7)
        self.assertEqual(finished.tokens_to_first_edit, 48000)
        self.assertNotIn("steps_to_first_edit", finished.nulls)

    def test_should_name_the_reason_the_first_edit_is_left_unmeasured(self):
        # Arrange
        counted = SessionSteps(main_steps=42, total_steps=54)
        rows = [
            ("no edit tool", NO_EDIT_TOOL, counted, None, "the client names no edit tool"),
            ("no transcript", EDIT_TOOLS, None, "the client reads no transcript", "the client reads no transcript"),
            ("no edit", EDIT_TOOLS, counted, None, "the segment made no edit outside the progress file"),
        ]
        for case, edit_tools, counted_steps, uncounted, reason in rows:
            with self.subTest(case=case):
                record = _create_counted_record(counted_steps=counted_steps, uncounted=uncounted, first_edit=None)

                # Act
                finished = describe_finished(_create_plan(edit_tools=edit_tools), record)

                # Assert
                self.assertEqual(finished.nulls["steps_to_first_edit"], reason)
                self.assertEqual(finished.nulls["tokens_to_first_edit"], reason)


class DescribeFinishedDigestsTest(unittest.TestCase):
    def test_should_record_the_digest_of_the_role_package_and_of_the_procedure(self):
        # Arrange
        record = _create_counted_record(counted_steps=None, uncounted="the client reads no transcript", first_edit=None)

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(finished.role_digest, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(finished.procedure_digest, "e395b77e8ab7354e4418d2e1bb9d6f5c5b4de99c417c8b5ac1bc588d5d5c4151")


class DescribeFinishedShippedBudgetTest(unittest.TestCase):
    def test_should_record_the_budget_the_package_of_the_role_ships(self):
        # Arrange
        record = _create_counted_record(counted_steps=None, uncounted="the client reads no transcript", first_edit=None)

        # Act
        finished = describe_finished(_create_plan(), record)

        # Assert
        self.assertEqual(finished.shipped_budget, 40)
