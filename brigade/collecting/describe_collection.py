from brigade.ledger.format_instant import format_instant
from brigade.runtime import Runtime

COLLECTOR_DOCUMENT_SCHEMA_VERSION = 1


def describe_collection(name: str, runtime: Runtime, summary: dict, items: list) -> dict:
    return {
        "schema_version": COLLECTOR_DOCUMENT_SCHEMA_VERSION,
        "collector": name,
        "collected_at": format_instant(runtime.now),
        "summary": summary,
        "items": items,
    }
