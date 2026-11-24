import argparse

from brigade.command import Argument, Command
from brigade.inbox.dismiss_signal import dismiss_signal
from brigade.inbox.find_signal import find_signal
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.read_inbox import DISMISSED_STATUS, read_inbox
from brigade.inbox.read_proposed_patterns import read_proposed_patterns
from brigade.inbox.read_repeated_pattern import read_repeated_pattern
from brigade.runtime import Runtime
from brigade.triage.dismiss_pattern import dismiss_pattern
from brigade.triage.is_pattern_defined import is_pattern_defined

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    if "pattern" in document:
        dismissed = (document["pattern"], *document["repeats"])
        return "dismissed " + " ".join(f"@PATTERN.{name}" for name in dismissed)
    named = f"{document['signal'][:SHOWN_ID_LENGTH]} {document['fingerprint']}"
    if document["changed"]:
        return f"dismissed {named}"
    return f"{named} is already dismissed"


def _read_repeats(runtime: Runtime, repeated: str) -> list[str]:
    patterns = read_proposed_patterns(runtime)
    names = sorted(pattern.name for pattern in patterns)
    return [pattern.name for pattern in patterns if read_repeated_pattern(pattern, names) == repeated]


def inbox_dismiss(request: argparse.Namespace, runtime: Runtime) -> dict:
    if is_pattern_defined(runtime, request.id):
        repeats = _read_repeats(runtime, request.id) if request.with_repeats else []
        for name in (request.id, *repeats):
            dismiss_pattern(runtime, name)
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, "pattern": request.id, "repeats": repeats}
    signal = find_signal(read_inbox(runtime.paths.state_root, runtime.now), request.id)
    changed = signal.status != DISMISSED_STATUS
    if changed:
        dismiss_signal(runtime.paths, runtime.now, signal)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "signal": signal.id,
        "fingerprint": signal.fingerprint,
        "changed": changed,
    }


COMMAND = Command(
    path=("inbox", "dismiss"),
    help="dismiss a signal, or a pattern with the signals it cites",
    arguments=(
        Argument(("--with-repeats",), {"action": "store_true", "help": "with the proposed patterns that repeat it"}),
        Argument(("id",), {"help": "the name of a PATTERN, or the id of a signal, 4 characters or more"}),
    ),
    run=inbox_dismiss,
    render_text=_render_text,
)
