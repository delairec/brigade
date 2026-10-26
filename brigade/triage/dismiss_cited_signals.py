from brigade.corpus.read_entity import Entity
from brigade.inbox.dismiss_signal import dismiss_signal
from brigade.inbox.is_signal_cited import is_signal_cited
from brigade.inbox.read_inbox import NEW_STATUS, read_inbox
from brigade.runtime import Runtime

EVIDENCE_FIELD = "EVIDENCE"


def dismiss_cited_signals(runtime: Runtime, pattern: Entity) -> None:
    evidence_lines = [field.value for field in pattern.fields if field.name == EVIDENCE_FIELD]
    for signal in read_inbox(runtime.paths.state_root, runtime.now):
        cited = any(is_signal_cited(evidence, signal.fingerprint) for evidence in evidence_lines)
        if cited and signal.status == NEW_STATUS:
            dismiss_signal(runtime.paths, runtime.now, signal)
