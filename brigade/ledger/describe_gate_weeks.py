from collections.abc import Iterable
from statistics import median

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.list_passed_pull_requests import PassedPullRequest, list_passed_pull_requests


def _name_week(pull_request: PassedPullRequest) -> str:
    year, week, _ = pull_request.passed_at.isocalendar()
    return f"{year}-W{week:02d}"


def _describe_week(week: str, passed: list[PassedPullRequest]) -> dict:
    escaped = sum(pull_request.escaped for pull_request in passed)
    return {
        "week": week,
        "passed": len(passed),
        "escaped": escaped,
        "escape_rate": f"{escaped}/{len(passed)}",
        "median_rounds": median(pull_request.rounds for pull_request in passed),
        "tasks": [{"task": pull_request.task, "rounds": pull_request.rounds} for pull_request in passed],
    }


def describe_gate_weeks(entries: Iterable[LedgerEntry]) -> list[dict]:
    weeks: dict[str, list[PassedPullRequest]] = {}
    for pull_request in list_passed_pull_requests(entries):
        weeks.setdefault(_name_week(pull_request), []).append(pull_request)
    return [_describe_week(week, weeks[week]) for week in sorted(weeks)]
