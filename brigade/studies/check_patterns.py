import json
from pathlib import Path

from brigade.corpus.read_entities import Entity, read_entities
from brigade.errors import BrigadeError
from brigade.inbox.is_signal_cited import is_signal_cited
from brigade.runtime import Runtime

PATTERN_TYPE = "PATTERN"
PROPOSED_STATUS = "new"
INBOX_FAMILIES = "inbox-families"


def _read_fingerprints(collected: list[dict]) -> tuple[str, ...]:
    return tuple(
        signal["fingerprint"]
        for entry in collected
        if entry["collector"] == INBOX_FAMILIES
        for family in json.loads(Path(entry["document"]).read_text(encoding="utf-8"))["items"]
        for signal in family["signals"]
    )


def _read_values(pattern: Entity, field_name: str) -> list[str]:
    return [field.value for field in pattern.fields if field.name == field_name]


def _check_pattern(pattern: Entity, fingerprints: tuple[str, ...]) -> None:
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
        if not any(is_signal_cited(evidence, fingerprint) for fingerprint in fingerprints):
            raise BrigadeError(
                f"{target}: the EVIDENCE {evidence!r} opens on the fingerprint of no signal {INBOX_FAMILIES} collected"
            )


def check_patterns(runtime: Runtime, directory: Path, collected: list[dict]) -> None:
    fingerprints = _read_fingerprints(collected)
    for pattern in read_entities(runtime.run_process, directory, PATTERN_TYPE):
        _check_pattern(pattern, fingerprints)
