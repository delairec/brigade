import re
from collections.abc import Callable

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.corpus.read_entities import read_entities
from brigade.inbox.is_signal_cited import is_signal_cited
from brigade.inbox.read_inbox import NEW_STATUS, Signal, read_inbox
from brigade.runtime import Runtime

NAME = "inbox-families"
PATTERN_TYPE = "PATTERN"
EVIDENCE_FIELD = "EVIDENCE"
CITED_RULE = re.compile(r"@RULE\.\w+")
PATH_KEY = "path"
CHECK_NAME_KEY = "name"
CHECK_RUN_KIND = "check_run"
SINGLE_SIGNAL = "signal"
SMALLEST_FAMILY = 2
NOT_CACHED = False


def _read_cited_rules(signal: Signal) -> list[str]:
    return sorted(
        {rule for text in signal.evidence.values() if isinstance(text, str) for rule in CITED_RULE.findall(text)}
    )


def _read_file(signal: Signal) -> list[str]:
    path = signal.evidence.get(PATH_KEY)
    return [path] if isinstance(path, str) else []


def _read_check_name(signal: Signal) -> list[str]:
    name = signal.evidence.get(CHECK_NAME_KEY)
    return [name] if signal.kind == CHECK_RUN_KIND and isinstance(name, str) else []


FAMILY_KEYS: tuple[tuple[str, Callable[[Signal], list[str]]], ...] = (
    ("rule", _read_cited_rules),
    ("file", _read_file),
    ("check", _read_check_name),
)


def _read_cited_evidence(runtime: Runtime) -> tuple[str, ...]:
    return tuple(
        field.value
        for pattern in read_entities(runtime.run_process, runtime.paths.config_root, PATTERN_TYPE)
        for field in pattern.fields
        if field.name == EVIDENCE_FIELD
    )


def _describe_signal(signal: Signal) -> dict:
    return {"id": signal.id, "fingerprint": signal.fingerprint, "evidence": signal.evidence}


def _group(signals: list[Signal]) -> list[dict]:
    families = []
    grouped = set()
    for by, read_keys in FAMILY_KEYS:
        members: dict[str, list[Signal]] = {}
        for signal in signals:
            for key in read_keys(signal):
                members.setdefault(key, []).append(signal)
        for key in sorted(members):
            if len(members[key]) >= SMALLEST_FAMILY:
                families.append({"by": by, "key": key, "signals": [_describe_signal(s) for s in members[key]]})
                grouped.update(signal.fingerprint for signal in members[key])
    alone = [signal for signal in signals if signal.fingerprint not in grouped]
    return families + [
        {"by": SINGLE_SIGNAL, "key": signal.fingerprint, "signals": [_describe_signal(signal)]} for signal in alone
    ]


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    cited_evidence = _read_cited_evidence(runtime)
    signals = sorted(
        (
            signal
            for signal in read_inbox(runtime.paths.state_root, runtime.now)
            if signal.status == NEW_STATUS
            and not any(is_signal_cited(evidence, signal.fingerprint) for evidence in cited_evidence)
        ),
        key=lambda signal: signal.fingerprint,
    )
    families = _group(signals)
    summary = {"families": len(families), "signals": len(signals)}
    return {**describe_collection(NAME, runtime, summary, families), "cache": NOT_CACHED}
