from collections import Counter

from brigade.ledger.count_by_name import count_by_name
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.tick_action_failed import TickActionFailed

DAY_FORMAT = "%Y-%m-%d"


def _describe_action(errors: list[str]) -> dict:
    return {"count": len(errors), "error": Counter(errors).most_common(1)[0][0]}


def describe_failed_actions(entries: tuple[LedgerEntry, ...]) -> dict:
    failed = [entry for entry in entries if isinstance(entry.event, TickActionFailed)]
    errors_by_action: dict[str, list[str]] = {}
    for entry in failed:
        errors_by_action.setdefault(entry.event.action, []).append(entry.event.error)
    return {
        "by_day": count_by_name(entry.instant.strftime(DAY_FORMAT) for entry in failed),
        "by_action": {action: _describe_action(errors) for action, errors in errors_by_action.items()},
    }
