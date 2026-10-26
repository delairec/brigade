import argparse
import dataclasses
import functools
import sys
from collections.abc import Callable

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.commands._read_forge_environment import FORGE_NAME, read_forge_environment
from brigade.commands.run import run
from brigade.errors import StandingDown, UsageError
from brigade.ledger.append_event import append_event
from brigade.ledger.format_instant import format_instant
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_rebased import TaskRebased
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_resumed import WaveResumed
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runs.create_run_id import create_run_id
from brigade.runs.read_run_document import read_run_document
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.runtime import Runtime
from brigade.studies.describe_wave_report import describe_wave_report
from brigade.studies.detach_study_run import detach_study_run
from brigade.studies.read_study import read_study
from brigade.studies.start_study_run import start_study_run
from brigade.system.ask_check_logs import CheckLogsQuery, ask_check_logs
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.ask_pull_request import PullRequestQuery, ask_pull_request
from brigade.system.hold_lock_without_waiting import hold_lock_without_waiting
from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT
from brigade.system.parse_configuration import Configuration
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.system.remove_expired_trails import remove_expired_trails
from brigade.system.repeat_until_signalled import repeat_until_signalled
from brigade.system.run_reporting_failure import run_reporting_failure
from brigade.system.trail_locations import TICKS_DIRECTORY, TRAIL_SUFFIX
from brigade.system.write_json_atomically import write_json_atomically
from brigade.tick.actions import (
    CloseWave,
    CutWaveBranch,
    LaunchCheckRepair,
    LaunchRemediation,
    LaunchStudy,
    LaunchTask,
    LaunchVerification,
    MergePullRequest,
    OpenIntegrationPullRequest,
    ParkTask,
    PauseWave,
    RebaseTask,
    RecordTaskState,
    RemoveTaskWorktree,
    ReportWave,
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
from brigade.tick.rebase_task import rebase_task
from brigade.tick.remove_task_worktree import remove_task_worktree
from brigade.tick.run_rounds import Rounds, run_rounds
from brigade.tick.write_build_brief import write_build_brief
from brigade.tick.write_repair_brief import write_repair_brief
from brigade.verify.preflight_pull_request import PreflightDemand, preflight_pull_request
from brigade.verify.record_verdict import REVIEW_SLOT
from brigade.waves.cut_wave_branch import WaveBranchCut, cut_wave_branch
from brigade.waves.find_wave_started import find_wave_started
from brigade.waves.start_project_wave import WaveStart, start_project_wave

DOCUMENT_SCHEMA_VERSION = 1
BUILD_PROCEDURE = "build-task"
BUILD_SLOT = "build"
VERIFY_PROCEDURE = "verify-pr"
REMEDIATE_PROCEDURE = "remediate-pr"
REMEDIATE_SLOT = "remediate"
REBASE_PROCEDURE = "rebase-on-base"
REBASE_SLOT = "rebase"
PR_OPEN_STATE = "pr_open"
FIXING_STATE = "fixing"
CHECK_LOG_LINES = 200
RUNNING_STATE = "running"
VERIFYING_STATE = "verifying"
MERGED_STATE = "merged"
PATH_FIELD = "PATH"
MAIN_FIELD = "MAIN"
NO_MILESTONE = None
UNKNOWN_OPENER = None
OPEN_PULL_REQUEST = "open"
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
    return runtime.paths.state_root / TICKS_DIRECTORY / f"{runtime.now.strftime(COMPACT_INSTANT_FORMAT)}{TRAIL_SUFFIX}"


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
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=RUNNING_STATE))
    run(building, runtime)


def _launch_verification(runtime: Runtime, configuration: Configuration, action: LaunchVerification) -> None:
    verifying = argparse.Namespace(
        procedure=configuration.procedures.get(REVIEW_SLOT, VERIFY_PROCEDURE),
        slot=REVIEW_SLOT,
        project=action.project,
        cwd=action.worktree,
        brief=None,
        arguments=(f"pr={action.pr}", f"task=@TASK.{action.task}"),
        run_id=None,
        wave=action.wave,
        task=action.task,
        detach=True,
        resume=False,
    )
    run(verifying, runtime)


def _launch_remediation(runtime: Runtime, configuration: Configuration, action: LaunchRemediation) -> None:
    remediating = argparse.Namespace(
        procedure=configuration.procedures.get(REMEDIATE_SLOT, REMEDIATE_PROCEDURE),
        slot=REMEDIATE_SLOT,
        project=action.project,
        cwd=action.worktree,
        brief=None,
        arguments=(f"pr={action.pr}", f"task=@TASK.{action.task}"),
        run_id=None,
        wave=action.wave,
        task=action.task,
        detach=True,
        resume=False,
    )
    run(remediating, runtime)
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=FIXING_STATE))


def _launch_check_repair(runtime: Runtime, configuration: Configuration, action: LaunchCheckRepair) -> None:
    logs = ask_check_logs(
        runtime.resolve_plugin("forge", FORGE_NAME),
        FORGE_NAME,
        CheckLogsQuery(
            repository=read_project_field(find_project(read_projects(runtime), action.project), PATH_FIELD),
            number=action.pr,
            checks=action.checks,
            lines=CHECK_LOG_LINES,
            environment=read_forge_environment(configuration, CLI_KEY, runtime),
        ),
        runtime,
    )
    repairing = argparse.Namespace(
        procedure=configuration.procedures.get(BUILD_SLOT, BUILD_PROCEDURE),
        slot=BUILD_SLOT,
        project=action.project,
        cwd=action.worktree,
        brief=str(write_repair_brief(runtime.paths.state_root, action, logs)),
        arguments=(f"task=@TASK.{action.task}", f"base={action.branch}"),
        run_id=None,
        wave=action.wave,
        task=action.task,
        detach=True,
        resume=False,
    )
    run(repairing, runtime)
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=FIXING_STATE))


def _launch_rebase(runtime: Runtime, configuration: Configuration, action: RebaseTask) -> None:
    rebasing = argparse.Namespace(
        procedure=configuration.procedures.get(REBASE_SLOT, REBASE_PROCEDURE),
        slot=REBASE_SLOT,
        project=action.project,
        cwd=action.worktree,
        brief=None,
        arguments=(f"pr={action.pr}", f"task=@TASK.{action.task}"),
        run_id=None,
        wave=action.wave,
        task=action.task,
        detach=True,
        resume=False,
    )
    run(rebasing, runtime)
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=FIXING_STATE))


def _rebase_task(runtime: Runtime, configuration: Configuration, action: RebaseTask) -> None:
    environment = read_forge_environment(configuration, CLI_KEY, runtime)
    login = ask_forge_account(runtime.resolve_plugin("forge", FORGE_NAME), FORGE_NAME, environment, runtime).login
    head = rebase_task(runtime, action, environment)
    if head is not None:
        append_event(
            runtime.paths,
            runtime.now,
            TaskRebased(wave=action.wave, task=action.task, before=action.head, after=head, login=login),
        )
        _record_task_state(
            runtime, RecordTaskState(wave=action.wave, task=action.task, state=PR_OPEN_STATE, reason=None)
        )
    elif action.parking_reason is not None:
        append_event(
            runtime.paths,
            runtime.now,
            TaskParked(wave=action.wave, task=action.task, reason=action.parking_reason, blockers=()),
        )
    else:
        _launch_rebase(runtime, configuration, action)


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
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=RUNNING_STATE))
    run(resuming, runtime)


def _launch_study(runtime: Runtime, action: LaunchStudy) -> None:
    study = read_study(runtime, action.study)
    run_id = create_run_id(runtime.now)
    start_study_run(runtime, study, run_id)
    detach_study_run(runtime, study.name, run_id, record_run_pid)


def _report_wave(runtime: Runtime, action: ReportWave) -> None:
    events = tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries)
    study = describe_wave_report(find_wave_started(events, action.wave))
    run_id = create_run_id(runtime.now)
    start_study_run(runtime, study, run_id)
    detach_study_run(runtime, study.name, run_id, record_run_pid)
    append_event(runtime.paths, runtime.now, WaveReported(wave=action.wave, run=run_id))


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


def _count_review_rounds(runtime: Runtime, action: MergePullRequest) -> int:
    return sum(
        1
        for entry in read_ledger(runtime.paths.state_root).entries
        if isinstance(entry.event, TaskVerdict) and entry.event.wave == action.wave and entry.event.task == action.task
    )


def _merge_pull_request(runtime: Runtime, configuration: Configuration, action: MergePullRequest) -> None:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    environment = read_forge_environment(configuration, CLI_KEY, runtime)
    project = find_project(read_projects(runtime), action.project)
    login = ask_forge_account(forge, FORGE_NAME, environment, runtime).login
    forge.merge_pull_request(
        {
            "repository": read_project_field(project, PATH_FIELD),
            "number": action.pr,
            "method": action.method,
            "environment": environment,
        },
        runtime,
    )
    append_event(
        runtime.paths,
        runtime.now,
        PrMerged(
            project=action.project,
            wave=action.wave,
            task=action.task,
            pr=action.pr,
            rounds=_count_review_rounds(runtime, action),
            login=login,
        ),
    )
    _record_task_state(runtime, RecordTaskState(wave=action.wave, task=action.task, state=MERGED_STATE, reason=None))


def _open_integration_pull_request(
    runtime: Runtime, configuration: Configuration, action: OpenIntegrationPullRequest
) -> None:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    environment = read_forge_environment(configuration, CLI_KEY, runtime)
    project = find_project(read_projects(runtime), action.project)
    main = read_project_field(project, MAIN_FIELD)
    repository = read_project_field(project, PATH_FIELD)
    query = PullRequestQuery(repository=repository, branch=action.branch, environment=environment)
    found = ask_pull_request(forge, FORGE_NAME, query, runtime)
    if found is not None and found.state == OPEN_PULL_REQUEST and found.base == main:
        append_event(runtime.paths, runtime.now, WavePrOpened(wave=action.wave, pr=found.number, login=UNKNOWN_OPENER))
        return
    login = ask_forge_account(forge, FORGE_NAME, environment, runtime).login
    tasks = ", ".join(f"@TASK.{task}" for task in action.tasks)
    opened = forge.open_pull_request(
        {
            "repository": repository,
            "base": main,
            "branch": action.branch,
            "title": f"chore(wave): merge the wave {action.wave} into {main}",
            "body": f"Integrates the wave {action.wave} of @PROJECT.{action.project} into {main}: {tasks}.",
            "milestone": NO_MILESTONE,
            "environment": environment,
        },
        runtime,
    )
    append_event(runtime.paths, runtime.now, WavePrOpened(wave=action.wave, pr=opened["number"], login=login))


def _cache_forge_environment(runtime: Runtime, configuration: Configuration) -> Callable[[str], dict]:
    return functools.cache(lambda key: read_forge_environment(configuration, key, runtime))


def _start_wave(runtime: Runtime, configuration: Configuration, action: StartWave) -> None:
    read_environment = _cache_forge_environment(runtime, configuration)
    start = WaveStart(project=action.project, tasks=(), configuration=configuration, read_environment=read_environment)
    start_project_wave(runtime, start)


def _cut_wave_branch(runtime: Runtime, configuration: Configuration, action: CutWaveBranch) -> None:
    cut = WaveBranchCut(
        project=find_project(read_projects(runtime), action.project),
        branch=action.branch,
        read_environment=_cache_forge_environment(runtime, configuration),
    )
    cut_wave_branch(runtime.run_process, cut)


def _park_task(runtime: Runtime, action: ParkTask) -> None:
    append_event(
        runtime.paths,
        runtime.now,
        TaskParked(wave=action.wave, task=action.task, reason=action.reason, blockers=action.blockers),
    )


def _pause_wave(runtime: Runtime, action: PauseWave) -> None:
    append_event(
        runtime.paths, runtime.now, WavePaused(wave=action.wave, reason=action.reason, resume_at=action.resume_at)
    )


def _list_executors(runtime: Runtime, configuration: Configuration) -> dict:
    return {
        RecordTaskState: lambda action: _record_task_state(runtime, action),
        ParkTask: lambda action: _park_task(runtime, action),
        RemoveTaskWorktree: lambda action: remove_task_worktree(runtime, action),
        RunPreflight: lambda action: _run_preflight(runtime, configuration, action),
        MergePullRequest: lambda action: _merge_pull_request(runtime, configuration, action),
        LaunchTask: lambda action: _launch_task(runtime, configuration, action),
        LaunchVerification: lambda action: _launch_verification(runtime, configuration, action),
        LaunchRemediation: lambda action: _launch_remediation(runtime, configuration, action),
        LaunchCheckRepair: lambda action: _launch_check_repair(runtime, configuration, action),
        RebaseTask: lambda action: _rebase_task(runtime, configuration, action),
        LaunchStudy: lambda action: _launch_study(runtime, action),
        PauseWave: lambda action: _pause_wave(runtime, action),
        ResumeWave: lambda action: append_event(
            runtime.paths, runtime.now, WaveResumed(wave=action.wave, reason=action.reason)
        ),
        ResumeTaskRun: lambda action: _resume_task_run(runtime, action),
        StartWave: lambda action: _start_wave(runtime, configuration, action),
        CutWaveBranch: lambda action: _cut_wave_branch(runtime, configuration, action),
        OpenIntegrationPullRequest: lambda action: _open_integration_pull_request(runtime, configuration, action),
        ReportWave: lambda action: _report_wave(runtime, action),
        CloseWave: lambda action: append_event(runtime.paths, runtime.now, WaveClosed(wave=action.wave, pr=action.pr)),
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
    started = runtime.read_monotonic()
    with hold_lock_without_waiting(_locate_lock(runtime)) as acquired:
        if not acquired:
            return None
        runtime.trail.locate(_locate_trail(runtime))
        configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
        read_pull_request = _follow_pull_requests(runtime, configuration)
        read_environment = _cache_forge_environment(runtime, configuration)
        outcome = run_rounds(
            Rounds(
                build_snapshot=lambda: build_snapshot(runtime, configuration, read_pull_request, read_environment),
                plan=plan,
                apply=functools.partial(
                    apply_actions,
                    executors=_list_executors(runtime, configuration),
                    record_failure=lambda event: append_event(runtime.paths, runtime.now, event),
                ),
                cap=ROUND_CAP,
            )
        )
        heartbeat = Heartbeat(
            ts=format_instant(runtime.now),
            duration_ms=int((runtime.read_monotonic() - started) * 1000),
            actions_applied=outcome.actions_applied,
            actions_failed=outcome.actions_failed,
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
        "actions_failed": heartbeat.actions_failed,
        "heartbeat": str(_locate_heartbeat(runtime)),
    }


def _plan_dry(runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    snapshot = build_snapshot(
        runtime,
        configuration,
        _follow_pull_requests(runtime, configuration),
        _cache_forge_environment(runtime, configuration),
    )
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
        f"brigade tick: {heartbeat.ts}: {heartbeat.actions_applied} actions applied,"
        f" {heartbeat.actions_failed} failed in {heartbeat.duration_ms} ms\n"
    )
    sys.stderr.flush()


def _tick_in_loop(create_runtime: Callable[[], Runtime]) -> dict:
    ticks_attempted = repeat_until_signalled(
        lambda: run_reporting_failure(lambda: _tick_and_report(create_runtime), COMMAND_NAME), TICK_INTERVAL_S
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "mode": "loop", "ticks_attempted": ticks_attempted}


def _render_once(document: dict) -> list[str]:
    applied = f"{document['actions_applied']} actions applied, {document['actions_failed']} failed"
    return [f"tick {document['ts']}: {applied} in {document['duration_ms']} ms"]


def _render_dry_run(document: dict) -> list[str]:
    snapshot_lines = [f"  {key}  {value}" for key, value in document["snapshot"].items() if key != "schema_version"]
    plan_lines = [f"  {action}" for action in document["plan"]] or ["  no action"]
    return ["snapshot", *snapshot_lines, "plan", *plan_lines]


def _render_loop(document: dict) -> list[str]:
    return [f"tick --loop: {document['ticks_attempted']} ticks attempted"]


RENDERERS = {"once": _render_once, "dry-run": _render_dry_run, "loop": _render_loop}


def _render_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["mode"]](document))


def tick(request: argparse.Namespace, runtime: Runtime) -> dict:
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
    render_text=_render_text,
)
