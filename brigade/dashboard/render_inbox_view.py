from html import escape
from urllib.parse import quote

from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.render_age import render_age
from brigade.triage.ratify_pattern import CONSTRAINT_ACTION, CONSTRAINT_KINDS

NO_PROJECT = "-"
NO_ACTION = "-"
NO_SIGNAL = "<p>no new signal</p>"
NO_PATTERN = "<p>no pattern proposed</p>"
RATIFY_ADDRESS = "/api/inbox/ratify/"
DISMISS_ADDRESS = "/api/inbox/dismiss/"


def _render_button(address: str, label: str) -> str:
    return f'<button data-post="{escape(address)}">{escape(label)}</button>'


def _render_signal(signal: dict) -> str:
    return (
        f"<li><code>{escape(signal['id'][:SHOWN_ID_LENGTH])}</code> {escape(signal['kind'])}"
        f" {escape(signal['project'] or NO_PROJECT)}, {signal['count']} in {escape(render_age(signal['age_s']))}"
        f" {_render_button(DISMISS_ADDRESS + quote(signal['id'], safe=''), 'dismiss')}</li>"
    )


def _render_family(family: dict, signals: dict) -> str:
    members = "".join(_render_signal(signals[signal]) for signal in family["signals"])
    return f"<section><h3>{escape(family['by'])} {escape(family['key'])}</h3><ul>{members}</ul></section>"


def _render_ratification(pattern: dict) -> str:
    address = RATIFY_ADDRESS + quote(pattern["name"], safe="")
    if pattern["action"] != CONSTRAINT_ACTION:
        return _render_button(address, "ratify")
    return "".join(_render_button(f"{address}?kind={kind}", f"ratify as {kind}") for kind in CONSTRAINT_KINDS)


def _render_pattern(pattern: dict) -> str:
    cited = "".join(f"<li><code>{escape(signal[:SHOWN_ID_LENGTH])}</code></li>" for signal in pattern["signals"])
    return (
        f"<article><h3>{escape(pattern['name'])}</h3><p>{escape(pattern['action'] or NO_ACTION)}</p>"
        f"<ul>{cited}</ul>{_render_ratification(pattern)}"
        f"{_render_button(DISMISS_ADDRESS + quote(pattern['name'], safe=''), 'dismiss')}</article>"
    )


def render_inbox_view(document: dict) -> str:
    signals = {signal["id"]: signal for signal in document["signals"]}
    families = "".join(_render_family(family, signals) for family in document["families"]) or NO_SIGNAL
    patterns = "".join(_render_pattern(pattern) for pattern in document["patterns"]) or NO_PATTERN
    return f"<section><h2>Signals</h2>{families}</section><section><h2>Patterns</h2>{patterns}</section>"
