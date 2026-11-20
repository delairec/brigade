from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_verdict import TaskVerdict

PASSING_VERDICT = "pass"


@dataclass(frozen=True)
class PassedPullRequest:
    task: str
    pr: int
    passed_at: datetime
    rounds: int
    escaped: bool


def _is_escaped(passed: PassedPullRequest, corrections: list[LedgerEntry]) -> bool:
    return any(entry.instant > passed.passed_at and passed.pr in entry.event.corrects for entry in corrections)


def list_passed_pull_requests(entries: Iterable[LedgerEntry]) -> tuple[PassedPullRequest, ...]:
    rounds: dict[int, int] = {}
    passed: dict[int, PassedPullRequest] = {}
    corrections = []
    for entry in entries:
        event = entry.event
        if isinstance(event, TaskPrOpened):
            corrections.append(entry)
        if not isinstance(event, TaskVerdict) or event.pr is None or event.pr in passed:
            continue
        rounds[event.pr] = rounds.get(event.pr, 0) + 1
        if event.verdict == PASSING_VERDICT:
            passed[event.pr] = PassedPullRequest(
                task=event.task, pr=event.pr, passed_at=entry.instant, rounds=rounds[event.pr], escaped=False
            )
    return tuple(
        PassedPullRequest(**{**vars(pull_request), "escaped": _is_escaped(pull_request, corrections)})
        for pull_request in passed.values()
    )
