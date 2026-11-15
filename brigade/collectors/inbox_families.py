from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.corpus.read_entities import Entity, read_entities
from brigade.inbox.group_signals import SignalFamily, group_signals
from brigade.inbox.is_signal_cited import is_signal_cited
from brigade.inbox.read_inbox import NEW_STATUS, Signal, read_inbox
from brigade.runtime import Runtime

NAME = "inbox-families"
PATTERN_TYPE = "PATTERN"
EVIDENCE_FIELD = "EVIDENCE"
TITLE_FIELD = "TITLE"
NOT_CACHED = False


def _read_cited_evidence(patterns: tuple[Entity, ...]) -> tuple[str, ...]:
    return tuple(field.value for pattern in patterns for field in pattern.fields if field.name == EVIDENCE_FIELD)


def _describe_pattern(pattern: Entity) -> dict:
    [title] = (field.value for field in pattern.fields if field.name == TITLE_FIELD)
    return {"name": pattern.name, "title": title}


def _describe_signal(signal: Signal) -> dict:
    return {"id": signal.id, "fingerprint": signal.fingerprint, "evidence": signal.evidence}


def _describe_family(family: SignalFamily) -> dict:
    return {"by": family.by, "key": family.key, "signals": [_describe_signal(signal) for signal in family.signals]}


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    patterns = read_entities(runtime.run_process, runtime.paths.config_root, PATTERN_TYPE)
    cited_evidence = _read_cited_evidence(patterns)
    signals = sorted(
        (
            signal
            for signal in read_inbox(runtime.paths.state_root, runtime.now)
            if signal.status == NEW_STATUS
            and not any(is_signal_cited(evidence, signal.fingerprint) for evidence in cited_evidence)
        ),
        key=lambda signal: signal.fingerprint,
    )
    families = [_describe_family(family) for family in group_signals(signals)]
    summary = {"families": len(families), "signals": len(signals)}
    return {
        **describe_collection(NAME, runtime, summary, families),
        "cache": NOT_CACHED,
        "patterns": [_describe_pattern(pattern) for pattern in patterns],
    }
