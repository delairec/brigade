from brigade.inbox.read_inbox import read_inbox
from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.runtime import Runtime

SIGNAL_KIND = "review_thread"
FINGERPRINT_PREFIX = "rt:"
EVIDENCE_FIELDS = ("pull_request", "path", "line", "author", "comment")


def _describe_signal(project: str, thread: dict) -> NewSignal:
    return NewSignal(
        kind=SIGNAL_KIND,
        project=project,
        fingerprint=f"{FINGERPRINT_PREFIX}{thread['thread']}",
        evidence={field: thread[field] for field in EVIDENCE_FIELDS},
    )


def record_review_threads(runtime: Runtime, project: str, threads: list[dict]) -> None:
    held = {signal.fingerprint for signal in read_inbox(runtime.paths.state_root, runtime.now)}
    for thread in threads:
        signal = _describe_signal(project, thread)
        if signal.fingerprint not in held:
            record_signal(runtime.paths, runtime.now, signal)
