import argparse

from brigade.command import Argument, Command
from brigade.corpus.read_entities import Entity
from brigade.inbox.group_signals import group_signals
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.is_signal_cited import is_signal_cited
from brigade.inbox.is_stall_stale import is_stall_stale
from brigade.inbox.read_inbox import NEW_STATUS, Signal, read_inbox
from brigade.inbox.read_proposed_patterns import read_proposed_patterns
from brigade.inbox.read_repeated_pattern import read_repeated_pattern
from brigade.inbox.read_study_answers import read_study_answers
from brigade.inbox.render_age import render_age
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
DOCUMENT_KIND = "progress_form"
OPERATIONAL_CORPUS_DOCUMENT = "awawa"
NO_SIGNAL = "no signal in the inbox"
NO_PROJECT = "-"
NO_ACTION = "-"
NO_CITED_SIGNAL = "-"
HEADER = ("id", "kind", "project", "count", "age", "status")
PATTERN_HEADER = ("pattern", "action", "signals")
ANSWER_HEADER = ("answer", "study", "project")
EVIDENCE_FIELD = "EVIDENCE"
LAST_ACTION_EVIDENCE = "last_action"
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


def _render_answer_row(answer: dict) -> tuple[str, ...]:
    return (answer["id"], answer["study"] or NO_PROJECT, answer["project"] or NO_PROJECT)


def _render_text(document: dict) -> str:
    signals = (
        render_table(HEADER, [_render_row(signal) for signal in document["signals"]])
        if document["signals"]
        else NO_SIGNAL
    )
    sections = [signals]
    if document["patterns"]:
        sections.append(
            render_table(PATTERN_HEADER, [_render_pattern_row(pattern) for pattern in document["patterns"]])
        )
    if document["answers"]:
        sections.append(render_table(ANSWER_HEADER, [_render_answer_row(answer) for answer in document["answers"]]))
    return SECTION_SEPARATOR.join(sections)


def _describe_pattern(pattern: Entity, signals: tuple[Signal, ...], names: list[str]) -> dict:
    evidence = [field.value for field in pattern.fields if field.name == EVIDENCE_FIELD]
    return {
        "name": pattern.name,
        "title": read_project_field(pattern, "TITLE"),
        "action": read_project_field(pattern, "ACTION"),
        "target": read_project_field(pattern, "TARGET"),
        "recipe": read_project_field(pattern, "RECIPE"),
        "repeats": read_repeated_pattern(pattern, names),
        "signals": [
            signal.id for signal in signals if any(is_signal_cited(cited, signal.fingerprint) for cited in evidence)
        ],
    }


def _describe_signal(signal: Signal, events: tuple) -> dict:
    return {
        "id": signal.id,
        "fingerprint": signal.fingerprint,
        "kind": signal.kind,
        "project": signal.project,
        "count": signal.count,
        "age_s": signal.age_s,
        "status": signal.status,
        "stale": is_stall_stale(signal, events),
        "last_action": signal.evidence.get(LAST_ACTION_EVIDENCE),
    }


def inbox_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    signals = read_inbox(runtime.paths.state_root, runtime.now)
    listed = [signal for signal in signals if request.all or signal.status == NEW_STATUS]
    events = tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries)
    patterns = read_proposed_patterns(runtime)
    names = sorted(pattern.name for pattern in patterns)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "signals": [_describe_signal(signal, events) for signal in listed],
        "families": [
            {"by": family.by, "key": family.key, "signals": [signal.id for signal in family.signals]}
            for family in group_signals(listed)
        ],
        "patterns": [_describe_pattern(pattern, signals, names) for pattern in patterns],
        "answers": [
            {"id": answer["id"], "study": answer["study"], "project": answer["project"]}
            for answer in read_study_answers(
                runtime, lambda: runtime.resolve_plugin(DOCUMENT_KIND, OPERATIONAL_CORPUS_DOCUMENT)
            )
        ],
    }


COMMAND = Command(
    path=("inbox", "list"),
    help="list the new signals of the inbox, their families, the proposed patterns and the study answers",
    group_help="list, show and dismiss the signals of the inbox and show its study answers",
    arguments=(Argument(("--all",), {"action": "store_true", "help": "add the dismissed signals"}),),
    run=inbox_list,
    render_text=_render_text,
)
