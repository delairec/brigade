import argparse
import dataclasses
import functools
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from brigade.collecting.collect_document import CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.command import Argument, Command, ExclusiveArguments
from brigade.commands._read_cli_login import read_cli_login
from brigade.commands._read_forge_environment import FORGE_KIND, FORGE_NAME, read_forge_environment
from brigade.commands.run import run
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import read_entities
from brigade.errors import StandingDown, UsageError
from brigade.inbox.record_check_runs import CheckRunsRecording, record_check_runs
from brigade.ledger.append_event import append_event
from brigade.ledger.format_instant import format_instant
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_preflighted import TaskPreflighted
from brigade.ledger.task_rebased import TaskRebased
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.tick_action_failed import TickActionFailed
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_merged import WaveMerged
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runs.create_run_id import create_run_id
from brigade.runs.list_runs import list_runs
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
from brigade.system.ask_review_threads import ReviewThreadsQuery, ask_review_threads
from brigade.system.collector_places import locate_collectors
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
    CloseMilestone,
    CloseWave,
    CollectCheckRuns,
    CollectReviewThreads,
    CutWaveBranch,
    LaunchCheckRepair,
    LaunchRemediation,
    LaunchStudy,
    LaunchTask,
    LaunchVerification,
    MergePullRequest,
    MergeWavePullRequest,
    OpenIntegrationPullRequest,
    OpenMilestonePullRequest,
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
from brigade.tick.build_snapshot import ForgeReaders, build_snapshot
from brigade.tick.heartbeat import Heartbeat
from brigade.tick.list_blocked_milestone_rebases import MilestoneRebasesReading, list_blocked_milestone_rebases
from brigade.tick.plan import plan
from brigade.tick.plan_connectors import plan_connectors
from brigade.tick.prepare_task_worktree import prepare_task_worktree
from brigade.tick.rebase_task import rebase_task
from brigade.tick.record_review_threads import record_review_threads
from brigade.tick.remove_task_worktree import remove_task_worktree
from brigade.tick.run_rounds import Rounds, RoundsOutcome, run_rounds
from brigade.tick.write_build_brief import write_build_brief
from brigade.tick.write_repair_brief import write_repair_brief
from brigade.triage.deliver_patterns import WaveDelivery, deliver_patterns
from brigade.verify.preflight_pull_request import PreflightDemand, preflight_pull_request
from brigade.verify.record_verdict import REVIEW_SLOT
from brigade.waves.cut_wave_branch import WaveBranchCut, cut_wave_branch
from brigade.waves.find_wave_started import find_wave_started
from brigade.waves.locate_project_main import locate_project_main
from brigade.waves.locate_wave_base import WaveBaseDemand, locate_wave_base
from brigade.waves.prepare_wave_tree import prepare_wave_tree
from brigade.waves.read_wave_milestone import read_wave_milestone
from brigade.waves.start_project_wave import WaveStart, start_project_wave

DOCUMENT_SCHEMA_VERSION = 1
BUILD_PROCEDURE = "build-task"
BUILD_SLOT = "build"
TASK_TYPE = "TASK"
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
COLLECTOR_KIND = "collector"
CHECK_RUNS_COLLECTOR = "check-runs"
REVIEW_THREADS_COLLECTOR = "pr-threads"
BEGINNING = date(1970, 1, 1)
NO_PARAMETERS = {}
NO_REFRESH = False


def _locate_heartbeat(runtime: Runtime):
    return runtime.paths.heartbeat_file


def _locate_lock(runtime: Runtime):
    return runtime.paths.lock_directory / LOCK_NAME


def _locate_trail(runtime: Runtime):
    return runtime.paths.state_root / TICKS_DIRECTORY / f"{runtime.now.strftime(COMPACT_INSTANT_FORMAT)}{TRAIL_SUFFIX}"


def _launch_rebase_of_the_branch(runtime: Runtime, configuration: Configuration, action: LaunchTask, worktree: Path):
    rebasing = argparse.Namespace(
        procedure=configuration.procedures.get(REBASE_SLOT, REBASE_PROCEDURE),
        slot=REBASE_SLOT,
        project=action.project,
        cwd=str(worktree),
        brief=None,
        arguments=(f"task=@TASK.{action.task}", f"base={action.branch}"),
        run_id=None,
        wave=action.wave,
        task=action.task,
        detach=True,
        resume=False,
    )
    append_event(runtime.paths, runtime.now, TaskState(wave=action.wave, task=action.task, state=RUNNING_STATE))
    run(rebasing, runtime)


def _launch_task(runtime: Runtime, configuration: Configuration, action: LaunchTask) -> None:
    prepared = prepare_task_worktree(runtime, configuration, action, _cache_forge_environment(runtime, configuration))
    if prepared.conflicted:
        _launch_rebase_of_the_branch(runtime, configuration, action, prepared.worktree.path)
        return
    worktree = prepared.worktree
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


def _close_wave(runtime: Runtime, action: CloseWave) -> None:
    deliver_patterns(runtime, WaveDelivery(project=action.project, milestones=action.milestones))
    append_event(runtime.paths, runtime.now, WaveClosed(wave=action.wave, pr=action.pr))


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


def _merge_on_the_forge(
    runtime: Runtime, configuration: Configuration, action: MergePullRequest | MergeWavePullRequest
) -> str:
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
    return login


def _merge_wave_pull_request(runtime: Runtime, configuration: Configuration, action: MergeWavePullRequest) -> None:
    login = _merge_on_the_forge(runtime, configuration, action)
    append_event(runtime.paths, runtime.now, WaveMerged(wave=action.wave, pr=action.pr, login=login))


def _merge_pull_request(runtime: Runtime, configuration: Configuration, action: MergePullRequest) -> None:
    login = _merge_on_the_forge(runtime, configuration, action)
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


def _find_started_wave(runtime: Runtime, wave: str) -> WaveStarted:
    return find_wave_started(tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries), wave)


def _locate_wave_base(runtime: Runtime, configuration: Configuration, started: WaveStarted, root: Path) -> str:
    tasks = {task.name: task for task in read_entities(runtime.run_process, root, TASK_TYPE)}
    demand = WaveBaseDemand(
        project=find_project(read_projects(runtime), started.project),
        milestone=read_wave_milestone(started.wave, (tasks[task] for task in started.tasks)),
        root=root,
        read_environment=_cache_forge_environment(runtime, configuration),
        read_login=functools.cache(lambda: read_cli_login(configuration, runtime)),
    )
    return locate_wave_base(runtime, demand)


def _locate_open_wave_base(runtime: Runtime, configuration: Configuration, wave: str) -> str:
    started = _find_started_wave(runtime, wave)
    root = prepare_wave_tree(runtime, configuration, started).root
    return _locate_wave_base(runtime, configuration, started, root)


def _locate_missing_wave_base(runtime: Runtime, configuration: Configuration, wave: str) -> str:
    started = _find_started_wave(runtime, wave)
    project = find_project(read_projects(runtime), started.project)
    main = locate_project_main(runtime.run_process, project, _cache_forge_environment(runtime, configuration))
    query = argparse.Namespace(project=project.name, ref=main, worktree=None)
    return _locate_wave_base(runtime, configuration, started, prepare_project_tree(query, configuration, runtime).root)


def _open_integration_pull_request(
    runtime: Runtime, configuration: Configuration, action: OpenIntegrationPullRequest
) -> None:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    environment = read_forge_environment(configuration, CLI_KEY, runtime)
    project = find_project(read_projects(runtime), action.project)
    base = _locate_open_wave_base(runtime, configuration, action.wave)
    repository = read_project_field(project, PATH_FIELD)
    query = PullRequestQuery(repository=repository, branch=action.branch, environment=environment)
    found = ask_pull_request(forge, FORGE_NAME, query, runtime)
    if found is not None and found.state == OPEN_PULL_REQUEST and found.base == base:
        append_event(runtime.paths, runtime.now, WavePrOpened(wave=action.wave, pr=found.number, login=UNKNOWN_OPENER))
        return
    login = ask_forge_account(forge, FORGE_NAME, environment, runtime).login
    tasks = ", ".join(f"@TASK.{task}" for task in action.tasks)
    opened = forge.open_pull_request(
        {
            "repository": repository,
            "base": base,
            "branch": action.branch,
            "title": f"chore(wave): merge the wave {action.wave} into {base}",
            "body": f"Integrates the wave {action.wave} of @PROJECT.{action.project} into {base}: {tasks}.",
            "milestone": NO_MILESTONE,
            "environment": environment,
        },
        runtime,
    )
    append_event(runtime.paths, runtime.now, WavePrOpened(wave=action.wave, pr=opened["number"], login=login))


def _open_milestone_pull_request(
    runtime: Runtime, configuration: Configuration, action: OpenMilestonePullRequest
) -> None:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    environment = read_forge_environment(configuration, CLI_KEY, runtime)
    project = find_project(read_projects(runtime), action.project)
    main = read_project_field(project, MAIN_FIELD)
    login = ask_forge_account(forge, FORGE_NAME, environment, runtime).login
    waves = ", ".join(f"{merged.wave} #{merged.pr}" for merged in action.waves)
    opened = forge.open_pull_request(
        {
            "repository": read_project_field(project, PATH_FIELD),
            "base": main,
            "branch": action.branch,
            "title": f"chore(milestone): merge the milestone {action.milestone} into {main}",
            "body": f"Merges the milestone {action.milestone} of @PROJECT.{action.project} into {main},"
            f" its waves merged: {waves}.",
            "milestone": NO_MILESTONE,
            "environment": environment,
        },
        runtime,
    )
    append_event(
        runtime.paths,
        runtime.now,
        MilestonePrOpened(project=action.project, milestone=action.milestone, pr=opened["number"], login=login),
    )


def _close_milestone(runtime: Runtime, action: CloseMilestone) -> None:
    append_event(
        runtime.paths, runtime.now, MilestoneClosed(project=action.project, milestone=action.milestone, pr=action.pr)
    )


def _cache_forge_environment(runtime: Runtime, configuration: Configuration) -> Callable[[str], dict]:
    return functools.cache(lambda key: read_forge_environment(configuration, key, runtime))


def _start_wave(runtime: Runtime, configuration: Configuration, action: StartWave) -> None:
    read_environment = _cache_forge_environment(runtime, configuration)
    start = WaveStart(
        project=action.project,
        tasks=(),
        configuration=configuration,
        read_environment=read_environment,
        read_login=functools.cache(lambda: read_cli_login(configuration, runtime)),
    )
    start_project_wave(runtime, start, action.milestone)


def _cut_wave_branch(runtime: Runtime, configuration: Configuration, action: CutWaveBranch) -> None:
    cut = WaveBranchCut(
        project=find_project(read_projects(runtime), action.project),
        branch=action.branch,
        read_environment=_cache_forge_environment(runtime, configuration),
    )
    cut_wave_branch(runtime.run_process, cut, _locate_missing_wave_base(runtime, configuration, action.wave))


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


def _collect_check_runs(runtime: Runtime, configuration: Configuration, action: CollectCheckRuns) -> None:
    path = Path(read_project_field(find_project(read_projects(runtime), action.project), PATH_FIELD))
    record_check_runs(
        runtime,
        CheckRunsRecording(
            project=action.project,
            path=path,
            collector=runtime.resolve_plugin(
                COLLECTOR_KIND, CHECK_RUNS_COLLECTOR, places=locate_collectors(path, runtime.paths)
            ),
            equipment=CollectorEquipment(
                configuration=configuration,
                forge=runtime.resolve_plugin("forge", FORGE_NAME),
                forge_name=FORGE_NAME,
            ),
        ),
    )


def _collect_review_threads(runtime: Runtime, configuration: Configuration, action: CollectReviewThreads) -> None:
    repository = Path(read_project_field(find_project(read_projects(runtime), action.project), PATH_FIELD))
    collector = runtime.resolve_plugin(
        COLLECTOR_KIND, REVIEW_THREADS_COLLECTOR, places=locate_collectors(repository, runtime.paths)
    )
    equipment = CollectorEquipment(
        configuration=configuration, forge=runtime.resolve_plugin(FORGE_KIND, FORGE_NAME), forge_name=FORGE_NAME
    )
    inputs = CollectorInputs(project=repository, since=BEGINNING, parameters=NO_PARAMETERS)
    collection = collect_document(
        collector, CollectionRequest(inputs=inputs, refresh=NO_REFRESH, equipment=equipment), runtime
    )
    record_review_threads(runtime, action.project, collection.document["items"])


def _list_executors(runtime: Runtime, configuration: Configuration) -> dict:
    return {
        RecordTaskState: lambda action: _record_task_state(runtime, action),
        ParkTask: lambda action: _park_task(runtime, action),
        RemoveTaskWorktree: lambda action: remove_task_worktree(runtime, action),
        RunPreflight: lambda action: _run_preflight(runtime, configuration, action),
        MergePullRequest: lambda action: _merge_pull_request(runtime, configuration, action),
        MergeWavePullRequest: lambda action: _merge_wave_pull_request(runtime, configuration, action),
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
        CloseWave: lambda action: _close_wave(runtime, action),
        OpenMilestonePullRequest: lambda action: _open_milestone_pull_request(runtime, configuration, action),
        CloseMilestone: lambda action: _close_milestone(runtime, action),
        CollectCheckRuns: lambda action: _collect_check_runs(runtime, configuration, action),
        CollectReviewThreads: lambda action: _collect_review_threads(runtime, configuration, action),
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


def _follow_review_threads(runtime: Runtime, configuration: Configuration) -> Callable[[str, int], int]:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    read_environment = functools.cache(lambda: read_forge_environment(configuration, CLI_KEY, runtime))
    return lambda repository, number: len(
        ask_review_threads(
            forge,
            FORGE_NAME,
            ReviewThreadsQuery(repository=repository, number=number, environment=read_environment()),
            runtime,
        )
    )


def _read_the_forge(runtime: Runtime, configuration: Configuration) -> ForgeReaders:
    return ForgeReaders(
        read_pull_request=_follow_pull_requests(runtime, configuration),
        read_environment=_cache_forge_environment(runtime, configuration),
        count_unresolved_threads=_follow_review_threads(runtime, configuration),
    )


def _plan_registered_connectors(runtime: Runtime) -> tuple:
    if not runtime.paths.schema_file.exists():
        return ()
    return plan_connectors(read_projects(runtime))


def _record_failure(runtime: Runtime, event: TickActionFailed) -> None:
    sys.stderr.write(f"brigade tick: {event.action} failed: {event.error}\n")
    append_event(runtime.paths, runtime.now, event)


def _name_the_blocked_milestone_rebases(runtime: Runtime, configuration: Configuration) -> None:
    if not runtime.paths.schema_file.exists():
        return
    reading = MilestoneRebasesReading(
        entries=read_ledger(runtime.paths.state_root).entries,
        runs=tuple(list_runs(runtime.paths.state_root)["runs"]),
        projects=read_projects(runtime),
        worktree_root=configuration.worktree_root,
    )
    for blocked in list_blocked_milestone_rebases(reading):
        sys.stderr.write(f"brigade tick: the rebase of {blocked.branch} is blocked: {blocked.question}\n")


def _apply_the_actions_of_the_tick(runtime: Runtime, configuration: Configuration) -> RoundsOutcome:
    _name_the_blocked_milestone_rebases(runtime, configuration)
    forge = _read_the_forge(runtime, configuration)
    apply = functools.partial(
        apply_actions,
        executors=_list_executors(runtime, configuration),
        record_failure=lambda event: _record_failure(runtime, event),
    )
    outcome = run_rounds(
        Rounds(
            build_snapshot=lambda: build_snapshot(runtime, configuration, forge),
            plan=plan,
            apply=apply,
            cap=ROUND_CAP,
        )
    )
    connectors = apply(_plan_registered_connectors(runtime))
    return RoundsOutcome(
        actions_applied=outcome.actions_applied + connectors.applied,
        actions_failed=outcome.actions_failed + len(connectors.failed),
    )


def _tick(runtime: Runtime) -> Heartbeat | None:
    started = runtime.read_monotonic()
    with hold_lock_without_waiting(_locate_lock(runtime)) as acquired:
        if not acquired:
            return None
        runtime.trail.locate(_locate_trail(runtime))
        outcome = _apply_the_actions_of_the_tick(runtime, read_configuration(runtime, CONFIGURATION_OPTIONAL))
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
    snapshot = build_snapshot(runtime, configuration, _read_the_forge(runtime, configuration))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "mode": "dry-run",
        "snapshot": snapshot.to_document(),
        "plan": [dataclasses.asdict(action) for action in (*plan(snapshot), *_plan_registered_connectors(runtime))],
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
