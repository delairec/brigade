from html import escape

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_card import render_awawa_card
from brigade.dashboard.render_empty_state import render_empty_state

SEVERITY_TONES = {"error": "failed", "warning": "you"}
NEUTRAL_TONE = "faint"
COUNTS = (("Errors", "errors"), ("Warnings", "warnings"), ("Unresolved references", "unresolved"))
HEALTHY_FILL = "A lint error or warning would be listed here."


def _judge_health(document: dict) -> str:
    if document["unresolved"]:
        return "No entity or file raises a lint error or warning."
    return "The corpus raises no diagnostic."


def _render_diagnostics(diagnostics: list[dict]) -> str:
    items = "".join(
        f'<li><span class="tone tone-{SEVERITY_TONES.get(diagnostic["severity"], NEUTRAL_TONE)}">'
        f"{escape(diagnostic['severity'])}</span> {escape(diagnostic['rule'])}"
        f" {escape(diagnostic['file'])}:{diagnostic['line']} {escape(diagnostic['message'])}</li>"
        for diagnostic in diagnostics
    )
    return f'<ul class="awawa-diagnostics">{items}</ul>'


def _render_entities(ailing: list[dict], address: AwawaAddress) -> str:
    items = "".join(
        f"<li>{render_awawa_card(patient['entity'], address)}{_render_diagnostics(patient['diagnostics'])}</li>"
        for patient in ailing
    )
    return f'<h3>Entities</h3><ul class="awawa-cards">{items}</ul>'


def _render_files(ailing: list[dict]) -> str:
    items = "".join(
        f"<li>{escape(patient['file'])}{_render_diagnostics(patient['diagnostics'])}</li>" for patient in ailing
    )
    return f'<h3>Files</h3><ul class="awawa-files">{items}</ul>'


def render_awawa_health(document: dict, address: AwawaAddress) -> str:
    counts = "".join(f"<div><dt>{label}</dt><dd>{document[key]}</dd></div>" for label, key in COUNTS)
    entities = _render_entities(document["entities"], address) if document["entities"] else ""
    files = _render_files(document["files"]) if document["files"] else ""
    healthy = "" if entities or files else render_empty_state(_judge_health(document), HEALTHY_FILL)
    return f'<div class="awawa-health"><dl class="awawa-counts">{counts}</dl>{healthy}{entities}{files}</div>'
