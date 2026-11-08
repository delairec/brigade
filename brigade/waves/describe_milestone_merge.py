from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.describe_merge_command import describe_merge_command
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.order_done import OrderDone
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_project_field import read_project_field
from brigade.waves.find_milestone_branch import find_milestone_branch

NOT_NAMED = None


def _is_report_committed(entries: tuple[LedgerEntry, ...], project: str, milestone: str | None) -> bool:
    runs = {
        entry.event.run
        for entry in entries
        if isinstance(entry.event, MilestoneReported)
        and (entry.event.project, entry.event.milestone) == (project, milestone)
    }
    return any(isinstance(entry.event, OrderDone) and entry.event.run in runs for entry in entries)


def _is_closed(entries: tuple[LedgerEntry, ...], project: str, milestone: str | None) -> bool:
    return any(
        isinstance(entry.event, MilestoneClosed)
        and (entry.event.project, entry.event.milestone) == (project, milestone)
        for entry in entries
    )


def describe_milestone_merge(entries: tuple[LedgerEntry, ...], project: Entity, milestone: str | None) -> str | None:
    if (
        is_on_a_forge(project)
        or not _is_report_committed(entries, project.name, milestone)
        or _is_closed(entries, project.name, milestone)
    ):
        return NOT_NAMED
    return describe_merge_command(
        Path(read_project_field(project, "PATH")), find_milestone_branch(entries, project.name, milestone)
    )
