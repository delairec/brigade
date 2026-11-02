import json
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity, read_entities
from brigade.errors import BrigadeError
from brigade.inbox.is_signal_cited import is_signal_cited
from brigade.runtime import Runtime

PATTERN_TYPE = "PATTERN"
PROPOSED_STATUS = "new"
INBOX_FAMILIES = "inbox-families"
TRANSCRIPT_FINDINGS = "transcript-findings"


def _read_signal_fingerprints(items: list[dict]) -> list[str]:
    return [signal["fingerprint"] for family in items for signal in family["signals"]]


def _read_finding_fingerprints(items: list[dict]) -> list[str]:
    return [finding["fingerprint"] for finding in items]


CITED_ITEMS_BY_COLLECTOR = {
    INBOX_FAMILIES: ("signal", _read_signal_fingerprints),
    TRANSCRIPT_FINDINGS: ("finding", _read_finding_fingerprints),
}


@dataclass(frozen=True)
class Citable:
    fingerprints: tuple[str, ...]
    described: str


def _read_citable(collected: list[dict]) -> Citable:
    cited = [entry for entry in collected if entry["collector"] in CITED_ITEMS_BY_COLLECTOR]
    fingerprints = []
    for entry in cited:
        _, read_fingerprints = CITED_ITEMS_BY_COLLECTOR[entry["collector"]]
        items = json.loads(Path(entry["document"]).read_text(encoding="utf-8"))["items"]
        fingerprints.extend(read_fingerprints(items))
    described = " or ".join(
        f"{CITED_ITEMS_BY_COLLECTOR[entry['collector']][0]} {entry['collector']}" for entry in cited
    )
    return Citable(fingerprints=tuple(fingerprints), described=described)


def _read_values(pattern: Entity, field_name: str) -> list[str]:
    return [field.value for field in pattern.fields if field.name == field_name]


def _check_pattern(pattern: Entity, citable: Citable) -> None:
    target = f"@{PATTERN_TYPE}.{pattern.name}"
    [status] = _read_values(pattern, "STATUS")
    if status != PROPOSED_STATUS:
        raise BrigadeError(f"{target} is {status}: a triage proposes it {PROPOSED_STATUS}")
    if not _read_values(pattern, "ACTION"):
        raise BrigadeError(f"{target} names no ACTION")
    evidence_lines = _read_values(pattern, "EVIDENCE")
    if not evidence_lines:
        raise BrigadeError(f"{target} holds no EVIDENCE")
    for evidence in evidence_lines:
        if not any(is_signal_cited(evidence, fingerprint) for fingerprint in citable.fingerprints):
            raise BrigadeError(
                f"{target}: the EVIDENCE {evidence!r} opens on the fingerprint of no {citable.described} collected"
            )


def check_patterns(runtime: Runtime, directory: Path, collected: list[dict]) -> None:
    citable = _read_citable(collected)
    for pattern in read_entities(runtime.run_process, directory, PATTERN_TYPE):
        _check_pattern(pattern, citable)
