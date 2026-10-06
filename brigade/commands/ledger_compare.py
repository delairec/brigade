from dataclasses import asdict

from brigade.ledger.describe_comparison import describe_comparison
from brigade.ledger.read_ledger import read_ledger

DOCUMENT_SCHEMA_VERSION = 1


def ledger_compare(request, runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **describe_comparison(reading, request.before),
        "skipped": [asdict(line) for line in reading.skipped],
    }
