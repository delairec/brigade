from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_reported import TaskReported
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.find_milestone_branch import find_milestone_branch

NOT_RECORDED = None


def _read_field(report: dict, name: str) -> str | None:
    return next((field["value"] for field in report["fields"] if field["name"] == name), None)


def _read_last(entries: tuple[LedgerEntry, ...], matches) -> LedgerEntry | None:
    return next((entry for entry in reversed(entries) if matches(entry.event)), NOT_RECORDED)


def _describe(waves: list[str], opened: LedgerEntry | None, reported: LedgerEntry | None) -> dict:
    return {
        "waves": waves,
        "pull_request": None if opened is None else opened.event.pr,
        "reported_at": None if reported is None else format_instant(reported.instant),
    }


def _describe_milestone(entries: tuple[LedgerEntry, ...], project: str, milestone: str) -> dict:
    branch = find_milestone_branch(entries, project, milestone)
    subject = (project, milestone)
    return _describe(
        [
            entry.event.wave
            for entry in entries
            if isinstance(entry.event, WaveStarted)
            and branch is not None
            and (entry.event.project, entry.event.branch) == (project, branch)
        ],
        _read_last(
            entries, lambda event: isinstance(event, MilestonePrOpened) and (event.project, event.milestone) == subject
        ),
        _read_last(
            entries, lambda event: isinstance(event, MilestoneReported) and (event.project, event.milestone) == subject
        ),
    )


def _describe_task(entries: tuple[LedgerEntry, ...], project: str, task: str) -> dict:
    subject = (project, task)
    return _describe(
        [
            entry.event.wave
            for entry in entries
            if isinstance(entry.event, WaveStarted) and entry.event.project == project and task in entry.event.tasks
        ],
        _read_last(entries, lambda event: isinstance(event, TaskPrOpened) and (event.project, event.task) == subject),
        _read_last(entries, lambda event: isinstance(event, TaskReported) and (event.project, event.task) == subject),
    )


def _describe_wave(entries: tuple[LedgerEntry, ...], wave: str) -> dict:
    return _describe(
        [wave],
        _read_last(entries, lambda event: isinstance(event, WavePrOpened) and event.wave == wave),
        _read_last(entries, lambda event: isinstance(event, WaveReported) and event.wave == wave),
    )


def describe_report_delivery(report: dict, entries: tuple[LedgerEntry, ...]) -> dict:
    project = report["project"]
    milestone = _read_field(report, "MILESTONE")
    if milestone is not None:
        return _describe_milestone(entries, project, milestone)
    task = _read_field(report, "TASK")
    if task is not None:
        return _describe_task(entries, project, task)
    wave = _read_field(report, "WAVE")
    if wave is not None:
        return _describe_wave(entries, wave)
    return _describe([], NOT_RECORDED, NOT_RECORDED)
