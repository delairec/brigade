import argparse

from brigade.command import Argument, Command
from brigade.corpus.read_entities import Entity, read_entities
from brigade.inbox.group_signals import group_signals
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.is_signal_cited import is_signal_cited
from brigade.inbox.read_inbox import NEW_STATUS, Signal, read_inbox
from brigade.inbox.render_age import render_age
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.render_table import render_table
from brigade.triage.read_new_pattern import NEW_STATUS as PROPOSED_STATUS
from brigade.triage.read_new_pattern import PATTERN_TYPE

DOCUMENT_SCHEMA_VERSION = 1
NO_SIGNAL = "no signal in the inbox"
NO_PROJECT = "-"
NO_ACTION = "-"
NO_CITED_SIGNAL = "-"
HEADER = ("id", "kind", "project", "count", "age", "status")
PATTERN_HEADER = ("pattern", "action", "signals")
EVIDENCE_FIELD = "EVIDENCE"
SECTION_SEPARATOR = "\n\n"


def _render_row(signal: dict) -> tuple[str, ...]:
    return (
        signal["id"][:SHOWN_ID_LENGTH],
        signal["kind"],
        signal["project"] or NO_PROJECT,
        str(signal["count"]),
        render_age(signal["age_s"]),
        signal["status"],
    )


def _render_pattern_row(pattern: dict) -> tuple[str, ...]:
    cited = " ".join(signal[:SHOWN_ID_LENGTH] for signal in pattern["signals"])
    return (pattern["name"], pattern["action"] or NO_ACTION, cited or NO_CITED_SIGNAL)


def _render_text(document: dict) -> str:
    signals = (
        render_table(HEADER, [_render_row(signal) for signal in document["signals"]])
        if document["signals"]
        else NO_SIGNAL
    )
    if not document["patterns"]:
        return signals
    patterns = render_table(PATTERN_HEADER, [_render_pattern_row(pattern) for pattern in document["patterns"]])
    return signals + SECTION_SEPARATOR + patterns


def _read_proposed_patterns(runtime: Runtime) -> tuple[Entity, ...]:
    if not runtime.paths.schema_file.exists():
        return ()
    patterns = read_entities(runtime.run_process, runtime.paths.config_root, PATTERN_TYPE)
    return tuple(pattern for pattern in patterns if read_project_field(pattern, "STATUS") == PROPOSED_STATUS)


def _describe_pattern(pattern: Entity, signals: tuple[Signal, ...]) -> dict:
    evidence = [field.value for field in pattern.fields if field.name == EVIDENCE_FIELD]
    return {
        "name": pattern.name,
        "action": read_project_field(pattern, "ACTION"),
        "signals": [
            signal.id for signal in signals if any(is_signal_cited(cited, signal.fingerprint) for cited in evidence)
        ],
    }


def inbox_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    signals = read_inbox(runtime.paths.state_root, runtime.now)
    listed = [signal for signal in signals if request.all or signal.status == NEW_STATUS]
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "signals": [
            {
                "id": signal.id,
                "fingerprint": signal.fingerprint,
                "kind": signal.kind,
                "project": signal.project,
                "count": signal.count,
                "age_s": signal.age_s,
                "status": signal.status,
            }
            for signal in listed
        ],
        "families": [
            {"by": family.by, "key": family.key, "signals": [signal.id for signal in family.signals]}
            for family in group_signals(listed)
        ],
        "patterns": [_describe_pattern(pattern, signals) for pattern in _read_proposed_patterns(runtime)],
    }


COMMAND = Command(
    path=("inbox", "list"),
    help="list the new signals of the inbox, their families and the proposed patterns",
    group_help="list, show and dismiss the signals of the inbox",
    arguments=(Argument(("--all",), {"action": "store_true", "help": "add the dismissed signals"}),),
    run=inbox_list,
    render_text=_render_text,
)
