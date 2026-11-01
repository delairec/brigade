from dataclasses import asdict

from brigade.ledger.describe_role_budget import CurrentDigests, describe_role_budget
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished

LATEST_RECORDED_DIGESTS = CurrentDigests(role=None, procedures={})


def describe_role_budgets(reading: LedgerReading) -> dict:
    segments = [entry.event for entry in reading.entries if isinstance(entry.event, RunFinished)]
    shipped = {segment.role: segment.shipped_budget for segment in segments if segment.shipped_budget is not None}
    return {
        role: asdict(
            describe_role_budget(
                tuple(segment for segment in segments if segment.role == role), shipped[role], LATEST_RECORDED_DIGESTS
            )
        )
        for role in sorted(shipped)
    }
