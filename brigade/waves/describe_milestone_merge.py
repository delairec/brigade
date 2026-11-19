from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.describe_merge_command import describe_merge_command
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_project_field import read_project_field
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.is_milestone_report_committed import is_milestone_report_committed

NOT_NAMED = None


def _is_closed(entries: tuple[LedgerEntry, ...], project: str, milestone: str | None) -> bool:
    return any(
        isinstance(entry.event, MilestoneClosed)
        and (entry.event.project, entry.event.milestone) == (project, milestone)
        for entry in entries
    )


def describe_milestone_merge(entries: tuple[LedgerEntry, ...], project: Entity, milestone: str | None) -> str | None:
    if (
        is_on_a_forge(project)
        or not is_milestone_report_committed(entries, project.name, milestone)
        or _is_closed(entries, project.name, milestone)
    ):
        return NOT_NAMED
    return describe_merge_command(
        Path(read_project_field(project, "PATH")), find_milestone_branch(entries, project.name, milestone)
    )
