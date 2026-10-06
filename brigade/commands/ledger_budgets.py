from dataclasses import asdict

from brigade.ledger.describe_budgets import describe_budgets
from brigade.ledger.read_ledger import read_ledger

DOCUMENT_SCHEMA_VERSION = 1


def run(request, runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **describe_budgets(reading, request.last),
        "skipped": [asdict(line) for line in reading.skipped],
    }
