import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from urllib.parse import parse_qs, urlsplit

from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_corpus_view import render_corpus_view
from brigade.dashboard.render_home import HomeDocuments, render_home
from brigade.dashboard.render_inbox_item import render_inbox_item
from brigade.dashboard.render_ledger_fragment import render_ledger_fragment
from brigade.dashboard.render_project_choice import render_project_choice
from brigade.dashboard.render_report_fragment import render_report_fragment
from brigade.dashboard.render_reports_fragment import render_reports_fragment
from brigade.dashboard.render_run_fragment import RunPage, render_run_fragment
from brigade.dashboard.render_runs_fragment import RunFilters, render_runs_fragment
from brigade.dashboard.render_wave import WavePage, render_wave
from brigade.dashboard.render_waves_view import OVERVIEW, render_waves_view
from brigade.dashboard.route_command import (
    PATH_SEPARATOR,
    PROJECT_LISTING,
    WAVE_LISTING,
    CommandRoute,
    route_command,
)
from brigade.dashboard.run_routed_command import OK, CommandAnswer

LEDGER_VIEW = "ledger"
WAVES_VIEW = "waves"
LEDGER_OVERVIEW = CommandRoute(arguments=("ledger", "--json"))
REPORTS_VIEW = "reports"
RUNS_VIEW = "runs"
CORPUS_VIEW = "corpus"
INBOX_VIEW = "inbox"
DOCUMENT = "document"
PROJECT = "project"
BUDGETS = "budgets"
TASK_RUNS = "task_runs"
WAVE = "wave"
LEDGER_BUDGETS = CommandRoute(arguments=("ledger", "budgets", "--json"))
WAVE_EVENTS = ("wave", "show", "--json", "--events")
STALE_SCHEDULER_EXIT_CODE = 1
REGION_ROUTES = {
    "heartbeat": CommandRoute(
        arguments=("scheduler", "status", "--json"), documented_exit_codes=(0, STALE_SCHEDULER_EXIT_CODE)
    ),
    "selector": CommandRoute(arguments=PROJECT_LISTING.arguments),
    "next-tick": CommandRoute(arguments=("tick", "--dry-run", "--json")),
}
HOME_VIEW = "status"
HOME_ROUTES = {
    DOCUMENT: CommandRoute(arguments=("status", "--json")),
    "scheduler": REGION_ROUTES["heartbeat"],
    "ledger": CommandRoute(arguments=("ledger", "--since", "1d", "--json")),
    "inbox": CommandRoute(arguments=("inbox", "list", "--json")),
}


def _follow_nothing(answers: dict[str, CommandAnswer]) -> dict[str, CommandRoute]:
    return {}


@dataclass(frozen=True)
class ViewRoute:
    routes: dict[str, CommandRoute]
    render: Callable[[dict[str, CommandAnswer]], str]
    follow: Callable[[dict[str, CommandAnswer]], dict[str, CommandRoute]] = _follow_nothing


def _render_reports(answers: dict[str, CommandAnswer]) -> str:
    return render_answer(answers[DOCUMENT], render_reports_fragment)


def _render_report(answers: dict[str, CommandAnswer]) -> str:
    return render_answer(answers[DOCUMENT], render_report_fragment)


def _render_home(answers: dict[str, CommandAnswer]) -> str:
    def render(status: dict) -> str:
        readings = {name: json.loads(answers[name].document) for name in ("scheduler", "ledger", "inbox")}
        return render_home(HomeDocuments(status=status, **readings))

    return render_answer(answers[DOCUMENT], render)


def _render_with(render: Callable[[dict], str]) -> Callable[[dict[str, CommandAnswer]], str]:
    return lambda answers: render_answer(answers[DOCUMENT], render)


def _follow_wave(answers: dict[str, CommandAnswer]) -> dict[str, CommandRoute]:
    shown = answers[DOCUMENT]
    if shown.status != OK:
        return {}
    project = json.loads(shown.document)["project"]
    return {PROJECT: CommandRoute(arguments=("project", "show", "--json", project))}


def _read_answered(answers: dict[str, CommandAnswer], name: str) -> dict | None:
    answer = answers.get(name)
    if answer is None or answer.status != OK:
        return None
    return json.loads(answer.document)


def _render_wave_page(answers: dict[str, CommandAnswer]) -> str:
    return render_answer(
        answers[DOCUMENT],
        lambda shown: render_wave(WavePage(shown=shown, project=_read_answered(answers, PROJECT))),
    )


def _render_run(answers: dict[str, CommandAnswer]) -> str:
    def render(shown: dict) -> str:
        page = RunPage(
            shown=shown,
            budgets=_read_answered(answers, BUDGETS),
            task_runs=_read_answered(answers, TASK_RUNS),
            wave=_read_answered(answers, WAVE),
        )
        return render_run_fragment(page)

    return render_answer(answers[DOCUMENT], render)


def _follow_run(answers: dict[str, CommandAnswer]) -> dict[str, CommandRoute]:
    shown = _read_answered(answers, DOCUMENT)
    if shown is None:
        return {}
    run = shown["run"]
    routes = {BUDGETS: LEDGER_BUDGETS}
    if run["task"] is not None:
        routes[TASK_RUNS] = CommandRoute(arguments=("ledger", "--task", run["task"], "--json"))
    if run["wave"] is not None:
        routes[WAVE] = CommandRoute(arguments=(*WAVE_EVENTS, run["wave"]))
    return routes


RENDERERS_BY_COLLECTION = {
    CORPUS_VIEW: _render_with(render_corpus_view),
    REPORTS_VIEW: _render_report,
    INBOX_VIEW: _render_with(render_inbox_item),
}


def _route_runs(route: CommandRoute, query: dict) -> ViewRoute:
    chosen = {name: query[name][0] if name in query else None for name in ("state", "wave", "task")}
    filters = RunFilters(**chosen)
    return ViewRoute(
        routes={DOCUMENT: route}, render=_render_with(lambda document: render_runs_fragment(document, filters))
    )


def _route_ledger(query: dict) -> ViewRoute:
    routes = {
        OVERVIEW: LEDGER_OVERVIEW,
        "budgets": CommandRoute(arguments=("ledger", "budgets", "--json")),
    }
    waves = query.get("wave", ())[:1]
    if waves:
        routes["wave"] = CommandRoute(arguments=(*WAVE_EVENTS, *waves))
    ranges = query.get("range", ())[:2]
    if ranges:
        routes["comparison"] = CommandRoute(
            arguments=("ledger", "compare", *(f"--range={value}" for value in ranges), "--json")
        )
    return ViewRoute(routes=routes, render=render_ledger_fragment)


def _route_waves() -> ViewRoute:
    return ViewRoute(
        routes={DOCUMENT: CommandRoute(arguments=WAVE_LISTING.arguments), OVERVIEW: LEDGER_OVERVIEW},
        render=render_waves_view,
    )


def route_view(target: str, renderers: dict[str, Callable[[dict], str]]) -> ViewRoute | None:
    address = urlsplit(target)
    if address.path in REGION_ROUTES:
        return ViewRoute(routes={DOCUMENT: REGION_ROUTES[address.path]}, render=_render_with(renderers[address.path]))
    if address.path == LEDGER_VIEW:
        return _route_ledger(parse_qs(address.query))
    if address.path == WAVES_VIEW:
        return _route_waves()
    if address.path == HOME_VIEW:
        return ViewRoute(routes=HOME_ROUTES, render=_render_home)
    route = route_command(target)
    if route is None:
        return None
    return _route_command_view(address.path, parse_qs(address.query), route, renderers)


def _route_command_view(
    path: str, query: dict, route: CommandRoute, renderers: dict[str, Callable[[dict], str]]
) -> ViewRoute:
    if route.listing == WAVE_LISTING:
        shown = replace(route, arguments=(*WAVE_EVENTS, route.identifier))
        return ViewRoute(routes={DOCUMENT: shown}, render=_render_wave_page, follow=_follow_wave)
    if path == RUNS_VIEW:
        return _route_runs(route, query)
    if path.startswith(f"{RUNS_VIEW}/"):
        return ViewRoute(routes={DOCUMENT: route}, render=_render_run, follow=_follow_run)
    if path in renderers:
        return ViewRoute(routes={DOCUMENT: route}, render=_render_with(renderers[path]))
    if path == CORPUS_VIEW:
        return ViewRoute(routes={DOCUMENT: route}, render=_render_with(render_project_choice))
    if path == REPORTS_VIEW:
        return ViewRoute(routes={DOCUMENT: route}, render=_render_reports)
    collection = path.split(PATH_SEPARATOR)[0]
    return ViewRoute(routes={DOCUMENT: route}, render=RENDERERS_BY_COLLECTION[collection])
