import json
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_corpus_view import render_corpus_view
from brigade.dashboard.render_fragment import render_fragment
from brigade.dashboard.render_ledger_fragment import render_ledger_fragment
from brigade.dashboard.render_project_choice import render_project_choice
from brigade.dashboard.render_report_fragment import render_report_fragment
from brigade.dashboard.render_reports_fragment import render_reports_fragment
from brigade.dashboard.render_run_fragment import render_run_fragment
from brigade.dashboard.render_wave import render_wave
from brigade.dashboard.route_command import WAVE_LISTING, CommandRoute, route_command
from brigade.dashboard.run_routed_command import OK, CommandAnswer

LEDGER_VIEW = "ledger"
REPORTS_VIEW = "reports"
RUNS_VIEW = "runs"
CORPUS_VIEW = "corpus"
DOCUMENT = "document"
WAVE_LEDGER = "ledger"
OPTIONAL_LEDGER_SECTIONS = {"wave": ("wave", ("ledger",)), "before": ("comparison", ("ledger", "compare"))}


@dataclass(frozen=True)
class ViewRoute:
    routes: dict[str, CommandRoute]
    render: Callable[[dict[str, CommandAnswer]], str]


def _render_document(answers: dict[str, CommandAnswer]) -> str:
    return render_fragment(json.loads(answers[DOCUMENT].document))


def _render_reports(answers: dict[str, CommandAnswer]) -> str:
    return render_answer(answers[DOCUMENT], render_reports_fragment)


def _render_report(answers: dict[str, CommandAnswer]) -> str:
    return render_answer(answers[DOCUMENT], render_report_fragment)


def _render_wave(answers: dict[str, CommandAnswer]) -> str:
    shown, ledger = answers[DOCUMENT], answers[WAVE_LEDGER]
    if shown.status == OK and ledger.status != OK:
        return render_fragment(json.loads(ledger.document))
    return render_answer(shown, lambda document: render_wave(document, json.loads(ledger.document)))


def _render_with(render: Callable[[dict], str]) -> Callable[[dict[str, CommandAnswer]], str]:
    return lambda answers: render_answer(answers[DOCUMENT], render)


def _route_ledger(query: dict) -> ViewRoute:
    routes = {
        "overview": CommandRoute(arguments=("ledger", "--json")),
        "budgets": CommandRoute(arguments=("ledger", "budgets", "--json")),
    }
    for parameter, (section, command) in OPTIONAL_LEDGER_SECTIONS.items():
        for value in query.get(parameter, ())[:1]:
            routes[section] = CommandRoute(arguments=(*command, f"--{parameter}={value}", "--json"))
    return ViewRoute(routes=routes, render=render_ledger_fragment)


def route_view(target: str, renderers: dict[str, Callable[[dict], str]]) -> ViewRoute | None:
    address = urlsplit(target)
    if address.path == LEDGER_VIEW:
        return _route_ledger(parse_qs(address.query))
    route = route_command(target)
    if route is None:
        return None
    if route.listing == WAVE_LISTING:
        ledger = CommandRoute(arguments=("ledger", "--json", f"--wave={route.identifier}"))
        return ViewRoute(routes={DOCUMENT: route, WAVE_LEDGER: ledger}, render=_render_wave)
    if address.path in renderers:
        return ViewRoute(routes={DOCUMENT: route}, render=_render_with(renderers[address.path]))
    if address.path == CORPUS_VIEW:
        return ViewRoute(routes={DOCUMENT: route}, render=_render_with(render_project_choice))
    if address.path.startswith(f"{CORPUS_VIEW}/"):
        return ViewRoute(routes={DOCUMENT: route}, render=_render_with(render_corpus_view))
    if address.path == REPORTS_VIEW:
        return ViewRoute(routes={DOCUMENT: route}, render=_render_reports)
    if address.path.startswith(f"{REPORTS_VIEW}/"):
        return ViewRoute(routes={DOCUMENT: route}, render=_render_report)
    if address.path.startswith(f"{RUNS_VIEW}/"):
        return ViewRoute(routes={DOCUMENT: route}, render=_render_with(render_run_fragment))
    return ViewRoute(routes={DOCUMENT: route}, render=_render_document)
