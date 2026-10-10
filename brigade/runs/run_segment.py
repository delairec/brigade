import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.compose_brief import BriefParts, compose_brief
from brigade.runs.count_session_steps import SessionSteps, count_session_steps
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import (
    BRIEF_FILE,
    PROGRESS_FILE,
    RESULT_FILE,
    ROLE_FILE,
    SEGMENTS_DIRECTORY,
    STDERR_FILE,
    STDOUT_FILE,
)
from brigade.runs.run_result import RunResult
from brigade.runs.segment_journal_writer import SegmentJournalWriter
from brigade.runs.sum_session_usage import sum_session_usage
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.client_role import ClientRole
from brigade.system.create_directory import create_directory
from brigade.system.launch_argv_request import LaunchArgvRequest
from brigade.system.parse_result_answer import ParseResultAnswer
from brigade.system.parse_result_request import ParseResultRequest
from brigade.system.process_trace import CUT, EXITED, ProcessTrace
from brigade.system.spawn_process import SpawnRequest
from brigade.system.transcripts_answer import TranscriptsAnswer
from brigade.system.transcripts_request import TranscriptsRequest
from brigade.system.wait_within_limit import WallLimit, wait_within_limit
from brigade.system.write_json_atomically import write_json_atomically
from brigade.system.write_text_file import write_text_file

FIRST_SEGMENT = 1
PROGRESS_FILE_VARIABLE = "BRIGADE_PROGRESS_FILE"
WALL_LIMIT_OUTCOME = "wall_limit"
GRACE_BEFORE_KILL_S = 30.0
NO_TRANSCRIPT_READ = "the client reads no transcript"
NO_SESSION_REPORTED = "the client reported no session"
NO_SESSION_AT_LAUNCH = "the client names no session at launch"


@dataclass(frozen=True)
class SegmentRecord:
    number: int
    result: RunResult
    exit_code: int | None
    measured_ms: int
    cost_usd: float | None
    counted_steps: SessionSteps | None
    uncounted: str | None


def _compose_segment_brief(plan: RunPlan, number: int) -> str:
    progress_file = plan.run_directory / PROGRESS_FILE
    progress = None if number == FIRST_SEGMENT else progress_file.read_text(encoding="utf-8")
    return compose_brief(
        BriefParts(
            progress=progress,
            procedure=plan.procedure.name,
            procedure_body=plan.procedure.body,
            arguments=plan.arguments,
            brief=plan.brief,
            progress_file=progress_file,
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


def _adopt_answer(answer: ParseResultAnswer, session_id: str | None) -> RunResult:
    return RunResult(
        outcome=answer.outcome,
        steps=answer.steps,
        usage=answer.usage,
        session_id=session_id,
        duration_ms=answer.duration_ms,
        error_class=answer.error_class,
        reset=answer.reset,
        message=answer.message,
    )


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


def _measure_cut(plan: RunPlan, runtime: Runtime, number: int, measured_ms: int, session_id: str | None):
    transcripts, uncounted = _read_transcripts(plan, runtime, session_id, NO_SESSION_AT_LAUNCH)
    cut = RunResult(
        outcome=WALL_LIMIT_OUTCOME,
        steps=None,
        usage=None if transcripts is None else sum_session_usage(transcripts),
        session_id=session_id,
        duration_ms=measured_ms,
        error_class=None,
        reset=None,
        message=f"cut at the wall-time limit of {plan.wall_limit_s:g} s",
    )
    return SegmentRecord(
        number=number,
        result=cut,
        exit_code=None,
        measured_ms=measured_ms,
        cost_usd=None,
        counted_steps=_count_steps(transcripts),
        uncounted=uncounted,
    )


def _run_process(plan: RunPlan, number: int, runtime: Runtime, segment_directory: Path) -> SegmentRecord:
    brief = _compose_segment_brief(plan, number)
    write_text_file(segment_directory / BRIEF_FILE, brief)
    progress_file = str(plan.run_directory / PROGRESS_FILE)
    launch = _ask_client(
        plan,
        runtime,
        LaunchArgvRequest(
            worktree=str(plan.worktree),
            brief=brief,
            role=_describe_role(plan),
            progress_file=progress_file,
            session_id=str(uuid.uuid4()),
        ),
    )
    request = SpawnRequest(
        argv=launch.argv,
        cwd=str(plan.worktree),
        environment={**launch.environment, **plan.forge_environment, PROGRESS_FILE_VARIABLE: progress_file},
        stdin=launch.stdin,
        stdout=segment_directory / STDOUT_FILE,
        stderr=segment_directory / STDERR_FILE,
    )
    started = time.monotonic()
    process = runtime.spawn_process(request)
    journal = SegmentJournalWriter(plan, number, runtime, segment_directory / STDOUT_FILE)
    limit = WallLimit(
        limit_s=plan.wall_limit_s, grace_before_kill_s=GRACE_BEFORE_KILL_S, poll_s=plan.configuration.journal_poll_s
    )
    exit_code = wait_within_limit(process, limit, journal.write_complete_lines)
    measured_ms = round((time.monotonic() - started) * 1000)
    journal.write_rest()
    outcome = CUT if exit_code is None else EXITED
    runtime.trail.append(ProcessTrace(request.argv, request.cwd, outcome, exit_code=exit_code, duration_ms=measured_ms))
    if exit_code is None:
        return _measure_cut(plan, runtime, number, measured_ms, launch.session_id)
    answer = _ask_client(
        plan,
        runtime,
        ParseResultRequest(
            exit_code=exit_code,
            stdout=(segment_directory / STDOUT_FILE).read_text(encoding="utf-8", errors="replace"),
            stderr=(segment_directory / STDERR_FILE).read_text(encoding="utf-8", errors="replace"),
        ),
    )
    session_id = launch.session_id if answer.session_id is None else answer.session_id
    transcripts, uncounted = _read_transcripts(plan, runtime, session_id, NO_SESSION_REPORTED)
    return SegmentRecord(
        number=number,
        result=_adopt_answer(answer, session_id),
        exit_code=exit_code,
        measured_ms=measured_ms,
        cost_usd=answer.cost_usd,
        counted_steps=_count_steps(transcripts),
        uncounted=uncounted,
    )


def run_segment(plan: RunPlan, number: int, runtime: Runtime) -> SegmentRecord:
    segment_directory = plan.run_directory / SEGMENTS_DIRECTORY / str(number)
    create_directory(segment_directory)
    record = _run_process(plan, number, runtime, segment_directory)
    write_json_atomically(segment_directory / RESULT_FILE, record.result.to_document())
    return record
