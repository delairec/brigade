import argparse
import dataclasses
import functools
import sys
import time
from collections.abc import Callable

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.commands.run import run
from brigade.errors import StandingDown, UsageError
from brigade.ledger.append_event import append_event
from brigade.ledger.format_instant import format_instant
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.runs.create_run_id import create_run_id
from brigade.runs.read_run_document import read_run_document
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.runtime import Runtime
from brigade.studies.detach_study_run import detach_study_run
from brigade.studies.read_study import read_study
from brigade.studies.start_study_run import start_study_run
from brigade.system.ask_pull_request import PullRequestQuery, ask_pull_request
from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting
from brigade.system.read_configuration import Configuration
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.remove_expired_trails import remove_expired_trails
from brigade.system.repeat_until_signalled import repeat_until_signalled
from brigade.system.run_reporting_failure import run_reporting_failure
from brigade.system.trail_locations import TICKS_DIRECTORY, TRAIL_INSTANT_FORMAT, TRAIL_SUFFIX
from brigade.system.write_json_atomically import write_json_atomically
from brigade.tick.actions import (
    LaunchStudy,
    LaunchTask,
    PauseWave,
    RecordTaskState,
    RemoveTaskWorktree,
    ResumeTaskRun,
    ResumeWave,
    RunPreflight,
    StartWave,
)
from brigade.tick.apply_actions import apply_actions
from brigade.tick.build_snapshot import build_snapshot
from brigade.tick.heartbeat import Heartbeat
from brigade.tick.plan import plan
from brigade.tick.prepare_task_worktree import prepare_task_worktree
from brigade.tick.remove_task_worktree import remove_task_worktree
from brigade.tick.run_rounds import Rounds, run_rounds
from brigade.tick.write_build_brief import write_build_brief
from brigade.verify.preflight_pull_request import PreflightDemand, preflight_pull_request
from brigade.waves.start_wave import start_wave

DOCUMENT_SCHEMA_VERSION = 1
BUILD_PROCEDURE = "build-task"
BUILD_SLOT = "build"
RUNNING_STATE = "running"
VERIFYING_STATE = "verifying"
FAILED_VERDICT = "fail"
TICK_INTERVAL_S = 300
ROUND_CAP = 10
LOCK_NAME = "tick.lock"
COMMAND_NAME = "tick"
CLI_KEY = "cli"


def _locate_heartbeat(runtime: Runtime):
    return runtime.paths.heartbeat_file


def _locate_lock(runtime: Runtime):
    return runtime.paths.lock_directory / LOCK_NAME


def _locate_trail(runtime: Runtime):
    return runtime.paths.state_root / TICKS_DIRECTORY / f"{runtime.now.strftime(TRAIL_INSTANT_FORMAT)}{TRAIL_SUFFIX}"


def _launch_task(runtime: Runtime, configuration: Configuration, action: LaunchTask) -> None:
    worktree = prepare_task_worktree(runtime, configuration, action)
    building = argparse.Namespace(
        procedure=configuration.procedures.get(BUILD_SLOT, BUILD_PROCEDURE),
        slot=BUILD_SLOT,
        project=action.project,
        cwd=str(worktree.path),
        brief=str(write_build_brief(runtime.paths.state_root, action, worktree)),
        arguments=(f"task=@TASK.{action.task}", f"base={action.branch}"),
        run_id=None,
        wave=action.wave,
        task=action.task,
        detach=True,
        resume=False,
    )
    run(building, runtime)
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=RUNNING_STATE))


def _resume_task_run(runtime: Runtime, action: ResumeTaskRun) -> None:
    record = RunRecord.from_document(
        read_run_document(
            runtime.paths.state_root / RUNS_DIRECTORY / action.run / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE
        )
    )
    resuming = argparse.Namespace(
        procedure=record.procedure_path,
        slot=record.slot,
        project=record.project,
        cwd=record.cwd,
        brief=record.brief,
        arguments=tuple(f"{key}={value}" for key, value in record.arguments.items()),
        run_id=record.run,
        wave=record.wave,
        task=record.task,
        detach=True,
        resume=True,
    )
    run(resuming, runtime)
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=RUNNING_STATE))


def _launch_study(runtime: Runtime, action: LaunchStudy) -> None:
    study = read_study(runtime, action.study)
    run_id = create_run_id(runtime.now)
    start_study_run(runtime, study, run_id)
    detach_study_run(runtime, study.name, run_id, record_run_pid)


def _record_task_state(runtime: Runtime, action: RecordTaskState) -> None:
    append_event(
        runtime.paths,
        runtime.now,
        TaskState(wave=action.wave, task=action.task, state=action.state, reason=action.reason),
    )


def _run_preflight(runtime: Runtime, configuration: Configuration, action: RunPreflight) -> None:
    findings = preflight_pull_request(
        runtime,
        PreflightDemand(
            project=find_project(read_projects(runtime), action.project),
            task=action.task,
            wave_branch=action.branch,
            pr=action.pr,
            forge=runtime.resolve_plugin("forge", FORGE_NAME),
            environment=read_forge_environment(configuration, CLI_KEY, runtime),
            configuration=configuration,
        ),
    )
    append_event(
        runtime.paths,
        runtime.now,
        TaskPreflighted(
            project=action.project,
            wave=action.wave,
            task=action.task,
            pr=action.pr,
            head=findings["head"],
            checks=tuple(findings["checks"]),
        ),
    )
    if all(check["verdict"] != FAILED_VERDICT for check in findings["checks"]):
        _record_task_state(
            runtime, RecordTaskState(wave=action.wave, task=action.task, state=VERIFYING_STATE, reason=None)
        )


def _list_executors(runtime: Runtime, configuration: Configuration) -> dict:
    return {
        StartWave: lambda action: start_wave(runtime, configuration, action.request),
        RecordTaskState: lambda action: _record_task_state(runtime, action),
        RemoveTaskWorktree: lambda action: remove_task_worktree(runtime, action),
        RunPreflight: lambda action: _run_preflight(runtime, configuration, action),
        LaunchTask: lambda action: _launch_task(runtime, configuration, action),
        LaunchStudy: lambda action: _launch_study(runtime, action),
        PauseWave: lambda action: append_event(
            runtime.paths,
            runtime.now,
            WavePaused(wave=action.wave, reason=action.reason, resume_at=action.resume_at),
        ),
        ResumeWave: lambda action: append_event(
            runtime.paths, runtime.now, WaveResumed(wave=action.wave, reason=action.reason)
        ),
        ResumeTaskRun: lambda action: _resume_task_run(runtime, action),
    }


def _follow_pull_requests(runtime: Runtime, configuration: Configuration) -> Callable:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    read_environment = functools.cache(lambda: read_forge_environment(configuration, CLI_KEY, runtime))
    return lambda repository, branch: ask_pull_request(
        forge,
        FORGE_NAME,
        PullRequestQuery(repository=repository, branch=branch, environment=read_environment()),
        runtime,
    )


def _tick(runtime: Runtime) -> Heartbeat | None:
    started = time.monotonic()
    with hold_lock_without_waiting(_locate_lock(runtime)) as acquired:
        if not acquired:
            return None
        runtime.trail.locate(_locate_trail(runtime))
        configuration = read_optional_configuration(runtime.paths.configuration_file)
        read_pull_request = _follow_pull_requests(runtime, configuration)
        outcome = run_rounds(
            Rounds(
                build_snapshot=lambda: build_snapshot(runtime, configuration, read_pull_request),
                plan=plan,
                apply=functools.partial(apply_actions, executors=_list_executors(runtime, configuration)),
                cap=ROUND_CAP,
            )
        )
        heartbeat = Heartbeat(
            ts=format_instant(runtime.now),
            duration_ms=int((time.monotonic() - started) * 1000),
            actions_applied=outcome.actions_applied,
        )
        write_json_atomically(_locate_heartbeat(runtime), heartbeat.to_document())
    return heartbeat


def _tick_once(runtime: Runtime) -> dict:
    heartbeat = _tick(runtime)
    if heartbeat is None:
        raise StandingDown(f"another tick holds {_locate_lock(runtime)}")
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "mode": "once",
        "ts": heartbeat.ts,
        "duration_ms": heartbeat.duration_ms,
        "actions_applied": heartbeat.actions_applied,
        "heartbeat": str(_locate_heartbeat(runtime)),
    }


def _plan_dry(runtime: Runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    snapshot = build_snapshot(runtime, configuration, _follow_pull_requests(runtime, configuration))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "mode": "dry-run",
        "snapshot": snapshot.to_document(),
        "plan": [dataclasses.asdict(action) for action in plan(snapshot)],
    }


def _tick_and_report(create_runtime: Callable[[], Runtime]) -> None:
    runtime = create_runtime()
    remove_expired_trails(runtime.paths, runtime.now)
    heartbeat = _tick(runtime)
    if heartbeat is None:
        sys.stderr.write(f"brigade tick: another tick holds {_locate_lock(runtime)}\n")
        return
    sys.stderr.write(
        f"brigade tick: {heartbeat.ts}: {heartbeat.actions_applied} actions applied in {heartbeat.duration_ms} ms\n"
    )
    sys.stderr.flush()


def _tick_in_loop(create_runtime: Callable[[], Runtime]) -> dict:
    ticks_attempted = repeat_until_signalled(
        lambda: run_reporting_failure(lambda: _tick_and_report(create_runtime), COMMAND_NAME), TICK_INTERVAL_S
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "mode": "loop", "ticks_attempted": ticks_attempted}


def _render_once(document: dict) -> list[str]:
    return [f"tick {document['ts']}: {document['actions_applied']} actions applied in {document['duration_ms']} ms"]


def _render_dry_run(document: dict) -> list[str]:
    snapshot_lines = [f"  {key}  {value}" for key, value in document["snapshot"].items() if key != "schema_version"]
    plan_lines = [f"  {action}" for action in document["plan"]] or ["  no action"]
    return ["snapshot", *snapshot_lines, "plan", *plan_lines]


def _render_loop(document: dict) -> list[str]:
    return [f"tick --loop: {document['ticks_attempted']} ticks attempted"]


RENDERERS = {"once": _render_once, "dry-run": _render_dry_run, "loop": _render_loop}


def _render_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["mode"]](document))


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def tick(request, runtime: Runtime) -> dict:
    if request.mode == "once":
        return _tick_once(runtime)
    if request.mode == "dry-run":
        return _plan_dry(runtime)
    if request.mode == "loop":
        return _tick_in_loop(request.create_runtime)
    raise UsageError(f"unknown mode {request.mode!r}: --once, --dry-run or --loop")


COMMAND = Command(
    path=("tick",),
    help="plan and apply what the facts call for, once or in a loop",
    arguments=(
        ExclusiveArguments(
            (
                Argument(
                    ("--once",), {"dest": "mode", "action": "store_const", "const": "once", "help": "run one tick"}
                ),
                Argument(
                    ("--dry-run",),
                    {
                        "dest": "mode",
                        "action": "store_const",
                        "const": "dry-run",
                        "help": "print the snapshot and the plan",
                    },
                ),
                Argument(
                    ("--loop",),
                    {
                        "dest": "mode",
                        "action": "store_const",
                        "const": "loop",
                        "help": "run a tick every five minutes until a signal",
                    },
                ),
            ),
            required=True,
        ),
    ),
    run=tick,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
