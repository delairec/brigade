import dataclasses
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.ask_progress import ask_progress
from brigade.runs.compose_brief import BriefParts, compose_brief
from brigade.runs.count_session_steps import SessionSteps, count_session_steps
from brigade.runs.decide_stop_at import decide_stop_at
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import (
    BRIEF_FILE,
    ROLE_FILE,
    SEGMENTS_DIRECTORY,
    STDERR_FILE,
    STDOUT_FILE,
)
from brigade.runs.segment_journal_writer import SegmentJournalWriter
from brigade.runs.sum_session_usage import sum_session_usage
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.client_role import ClientRole
from brigade.system.create_directory import create_directory
from brigade.system.launch_argv_request import LaunchArgvRequest
from brigade.system.parse_result_request import ParseResultRequest
from brigade.system.process_trace import CUT, EXITED, STOPPED, ProcessTrace
from brigade.system.reset_hour import ResetHour
from brigade.system.spawn_process import SpawnRequest
from brigade.system.stop_process_group import stop_process_group
from brigade.system.stop_signal_receiver import StopRequested, StopSignalReceiver
from brigade.system.token_usage import TokenUsage
from brigade.system.transcripts_answer import TranscriptsAnswer
from brigade.system.transcripts_request import TranscriptsRequest
from brigade.system.wait_within_limit import WallLimit, wait_within_limit
from brigade.system.write_text_file import write_text_file

FIRST_SEGMENT = 1
PROGRESS_FILE_VARIABLE = "BRIGADE_PROGRESS_FILE"
WALL_LIMIT_OUTCOME = "wall_limit"
STOPPED_OUTCOME = "stopped"
FAILED_OUTCOME = "failed"
STOPPED_BY_A_SIGNAL = "stopped by a signal"
NOT_LAUNCHED = "the client was never launched"
NOT_MEASURED_MS = 0
TURN_LIMIT = "turn_limit"
GRACE_BEFORE_KILL_S = 30.0
NO_TRANSCRIPT_READ = "the client reads no transcript"
NO_SESSION_REPORTED = "the client reported no session"
NO_SESSION_AT_LAUNCH = "the client names no session at launch"


@dataclass(frozen=True)
class SegmentRecord:
    number: int
    outcome: str
    session_id: str | None
    client_steps: int | None
    usage: TokenUsage | None
    error_class: str | None
    reset: ResetHour | None
    message: str | None
    exit_code: int | None
    measured_ms: int
    cost_usd: float | None
    counted_steps: SessionSteps | None
    uncounted: str | None
    adapter_failure: str | None


def _compose_segment_brief(plan: RunPlan, number: int, runtime: Runtime) -> str:
    progress = None if number == FIRST_SEGMENT else ask_progress(plan, "read_document", runtime).text
    return compose_brief(
        BriefParts(
            progress=progress,
            procedure=plan.procedure.name,
            procedure_body=plan.procedure.body,
            arguments=plan.arguments,
            brief=plan.brief,
            progress_description=ask_progress(plan, "describe_document", runtime).text,
        )
    )


def _describe_role(plan: RunPlan) -> ClientRole:
    return ClientRole(
        name=plan.role.role,
        package=plan.role.body,
        package_file=str(plan.run_directory / ROLE_FILE),
        capabilities=plan.capabilities,
        reasoning=plan.role.front_matter["reasoning"],
        budget=plan.procedure.budget,
    )


def _ask_client(plan: RunPlan, runtime: Runtime, request: LaunchArgvRequest | ParseResultRequest | TranscriptsRequest):
    return ask_named_client(plan.client_adapter, ClientQuestion(plan.client, request), plan.configuration, runtime)


def _read_transcripts(
    plan: RunPlan, runtime: Runtime, session_id: str | None, no_session: str
) -> tuple[TranscriptsAnswer | None, str | None]:
    if not plan.reads_transcripts:
        return None, NO_TRANSCRIPT_READ
    if session_id is None:
        return None, no_session
    try:
        return _ask_client(plan, runtime, TranscriptsRequest(session_id=session_id, worktree=str(plan.worktree))), None
    except BrigadeError as error:
        return None, f"the transcript could not be read: {error}"


def _count_steps(transcripts: TranscriptsAnswer | None) -> SessionSteps | None:
    return None if transcripts is None else count_session_steps(transcripts)


def _describe_ending(
    number: int, outcome: str, message: str, session_id: str | None, measured_ms: int
) -> SegmentRecord:
    return SegmentRecord(
        number=number,
        outcome=outcome,
        session_id=session_id,
        client_steps=None,
        usage=None,
        error_class=None,
        reset=None,
        message=message,
        exit_code=None,
        measured_ms=measured_ms,
        cost_usd=None,
        counted_steps=None,
        uncounted=NOT_LAUNCHED,
        adapter_failure=None,
    )


def _measure_ending(plan: RunPlan, runtime: Runtime, ending: SegmentRecord) -> SegmentRecord:
    transcripts, uncounted = _read_transcripts(plan, runtime, ending.session_id, NO_SESSION_AT_LAUNCH)
    return dataclasses.replace(
        ending,
        usage=None if transcripts is None else sum_session_usage(transcripts),
        counted_steps=_count_steps(transcripts),
        uncounted=uncounted,
    )


def _record_ending_before_launch(number: int, outcome: str, message: str, session_id: str | None) -> SegmentRecord:
    return _describe_ending(number, outcome, message, session_id, NOT_MEASURED_MS)


def _wait_for_client(process, limit: WallLimit, on_poll, stop: StopSignalReceiver) -> tuple[int | None, str]:
    try:
        with stop.raising():
            exit_code = wait_within_limit(process, limit, stop.holding()(on_poll))
    except StopRequested:
        stop_process_group(process, limit.grace_before_kill_s)
        return None, STOPPED
    return exit_code, CUT if exit_code is None else EXITED


def _run_process(
    plan: RunPlan, number: int, runtime: Runtime, segment_directory: Path, stop: StopSignalReceiver
) -> SegmentRecord:
    brief = _compose_segment_brief(plan, number, runtime)
    write_text_file(segment_directory / BRIEF_FILE, brief)
    progress_file = str(plan.progress_file)
    try:
        launch = _ask_client(
            plan,
            runtime,
            LaunchArgvRequest(
                worktree=str(plan.worktree),
                brief=brief,
                role=_describe_role(plan),
                progress_file=progress_file,
                session_id=str(uuid.uuid4()),
                stop_at=decide_stop_at(runtime.read_clock(), plan.wall_limit_s, plan.configuration.soft_limit_margin_s),
            ),
        )
    except BrigadeError as error:
        record = _record_ending_before_launch(number, FAILED_OUTCOME, str(error), None)
        return dataclasses.replace(record, adapter_failure=str(error))
    request = SpawnRequest(
        argv=launch.argv,
        cwd=str(plan.worktree),
        environment={**launch.environment, **plan.forge_environment, PROGRESS_FILE_VARIABLE: progress_file},
        stdin=launch.stdin,
        stdout=segment_directory / STDOUT_FILE,
        stderr=segment_directory / STDERR_FILE,
    )
    if stop.requested:
        return _record_ending_before_launch(number, STOPPED_OUTCOME, STOPPED_BY_A_SIGNAL, launch.session_id)
    started = time.monotonic()
    process = runtime.spawn_process(request)
    journal = SegmentJournalWriter(plan, number, runtime, segment_directory / STDOUT_FILE)
    limit = WallLimit(
        limit_s=plan.wall_limit_s, grace_before_kill_s=GRACE_BEFORE_KILL_S, poll_s=plan.configuration.journal_poll_s
    )
    exit_code, outcome = _wait_for_client(process, limit, journal.write_complete_lines, stop)
    measured_ms = round((time.monotonic() - started) * 1000)
    journal.write_rest()
    runtime.trail.append(ProcessTrace(request.argv, request.cwd, outcome, exit_code=exit_code, duration_ms=measured_ms))
    if outcome == STOPPED:
        ending = _describe_ending(number, STOPPED_OUTCOME, STOPPED_BY_A_SIGNAL, launch.session_id, measured_ms)
        return _measure_ending(plan, runtime, ending)
    if outcome == CUT:
        cut = f"cut at the wall-time limit of {plan.wall_limit_s:g} s"
        return _measure_ending(
            plan, runtime, _describe_ending(number, WALL_LIMIT_OUTCOME, cut, launch.session_id, measured_ms)
        )
    try:
        answer = _ask_client(
            plan,
            runtime,
            ParseResultRequest(
                exit_code=exit_code,
                stdout=(segment_directory / STDOUT_FILE).read_text(encoding="utf-8", errors="replace"),
                stderr=(segment_directory / STDERR_FILE).read_text(encoding="utf-8", errors="replace"),
            ),
        )
    except BrigadeError as error:
        ending = _describe_ending(number, FAILED_OUTCOME, str(error), launch.session_id, measured_ms)
        record = _measure_ending(plan, runtime, ending)
        return dataclasses.replace(record, exit_code=exit_code, adapter_failure=str(error))
    session_id = launch.session_id if answer.session_id is None else answer.session_id
    transcripts, uncounted = _read_transcripts(plan, runtime, session_id, NO_SESSION_REPORTED)
    return SegmentRecord(
        number=number,
        outcome=TURN_LIMIT if answer.error_class == TURN_LIMIT else answer.outcome,
        session_id=session_id,
        client_steps=answer.steps,
        usage=answer.usage,
        error_class=answer.error_class,
        reset=answer.reset,
        message=answer.message,
        exit_code=exit_code,
        measured_ms=measured_ms,
        cost_usd=answer.cost_usd,
        counted_steps=_count_steps(transcripts),
        uncounted=uncounted,
        adapter_failure=None,
    )


def run_segment(plan: RunPlan, number: int, runtime: Runtime, stop: StopSignalReceiver) -> SegmentRecord:
    segment_directory = plan.run_directory / SEGMENTS_DIRECTORY / str(number)
    create_directory(segment_directory)
    return _run_process(plan, number, runtime, segment_directory, stop)
