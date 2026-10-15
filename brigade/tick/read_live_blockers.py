from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.tick.read_awawa_document import read_awawa_document

BLOCKING_CONVERSE = ["BLOCKED_BY"]
SUPPRESSED_GATE = ["suppressed"]
STATUS_FIELD = "STATUS"


def _holds(entry: dict, name: str, atoms: list[str]) -> bool:
    return any(nested["name"] == name and nested["atoms"] == atoms for nested in entry["fields"])


def _read_blocking_fields(schema: dict) -> set[str]:
    return {
        entry["atoms"][0]
        for entry in schema["fields"]
        if entry["name"] == "FIELD" and _holds(entry, "CONVERSE", BLOCKING_CONVERSE)
    }


def _read_suppressed_statuses(schema: dict) -> set[str]:
    return {
        entry["atoms"][1]
        for entry in schema["fields"]
        if entry["name"] == "WHEN" and entry["atoms"][0] == STATUS_FIELD and _holds(entry, "GATE", SUPPRESSED_GATE)
    }


def _is_live_blocker(site: dict, schema: dict) -> bool:
    cited_through_a_blocking_field = site["field_path"][0] in _read_blocking_fields(schema)
    return cited_through_a_blocking_field and site["from"]["status"] not in _read_suppressed_statuses(schema)


def read_live_blockers(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, task: str
) -> tuple[str, ...]:
    sites = read_awawa_document(run_process, root, ("refs", f"@TASK.{task}"))["incoming"]
    schemas = {
        citing_type: read_awawa_document(run_process, root, ("show", citing_type))
        for citing_type in {site["from"]["type"] for site in sites}
    }
    return tuple(
        f"{site['from']['type']}.{site['from']['name']}"
        for site in sites
        if _is_live_blocker(site, schemas[site["from"]["type"]])
    )
