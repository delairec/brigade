import hmac
import json
from importlib.resources import files
from string import Template
from urllib.parse import parse_qs, urlsplit

from brigade.dashboard.dashboard_exchange import LOOPBACK_HOST, Dashboard, DashboardResponse, IncomingRequest
from brigade.dashboard.read_awawa_address import read_awawa_address
from brigade.dashboard.render_addons_rail import render_addons_rail
from brigade.dashboard.render_awawa_tab import render_awawa_tab
from brigade.dashboard.render_heartbeat import render_heartbeat
from brigade.dashboard.render_inbox_view import render_inbox_view
from brigade.dashboard.render_next_tick import render_next_tick
from brigade.dashboard.render_project_selector import render_project_selector
from brigade.dashboard.route_action import route_action
from brigade.dashboard.route_change import route_change
from brigade.dashboard.route_command import CommandRoute, route_command
from brigade.dashboard.route_view import REGION_ROUTES, route_view
from brigade.dashboard.run_routed_command import CommandAnswer, run_routed_command
from brigade.dashboard.select_project_rows import select_project_rows
from brigade.runtime import Runtime

PAGE_DATA = files("brigade.dashboard") / "data"
HTML = "text/html; charset=utf-8"
JSON = "application/json"
PAGE_PATH = "/"
PAGE_FILE = "index.html"
ASSETS = {
    "/dashboard.js": ("dashboard.js", "text/javascript; charset=utf-8"),
    "/dashboard.css": ("dashboard.css", "text/css; charset=utf-8"),
}
API_PREFIX = "/api/"
AWAWA_PREFIX = "/api/awawa/"
ADDON_PARAMETERS = ("ref", "view", "type", "field", "search", "entity")
ADDON_FILTER = "filter"
PATH_SEPARATOR = "/"
VIEWS_PREFIX = "/views/"
READING_METHOD = "GET"
STATE_CHANGING_METHOD = "POST"
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
OK = 200
VIEW_RENDERERS = {"inbox": render_inbox_view, "next-tick": render_next_tick}
PROJECT_PARAMETER = "project"
ADDONS_REGION = "addons"
VIEW_PARAMETER = "view"
FIRST_AWAWA_VIEW = "tree"


def _answer_error(status: int, message: str) -> DashboardResponse:
    return DashboardResponse(status=status, content_type=JSON, body=json.dumps({"error": message}).encode())


def _carries_the_token(incoming: IncomingRequest, dashboard: Dashboard) -> bool:
    token = (incoming.token or "").encode()
    return incoming.origin == dashboard.origin and hmac.compare_digest(token, dashboard.token.encode())


def _refuse(incoming: IncomingRequest, dashboard: Dashboard) -> DashboardResponse | None:
    if incoming.host != f"{LOOPBACK_HOST}:{dashboard.port}":
        return _answer_error(BAD_REQUEST, "the Host header is not the address this server listens on")
    if incoming.method == STATE_CHANGING_METHOD and not _carries_the_token(incoming, dashboard):
        return _answer_error(FORBIDDEN, "a POST carries the token of the page and its origin")
    return None


def _answer_page(dashboard: Dashboard) -> DashboardResponse:
    page = Template((PAGE_DATA / PAGE_FILE).read_text(encoding="utf-8")).substitute(token=dashboard.token)
    return DashboardResponse(status=OK, content_type=HTML, body=page.encode())


def _answer_asset(path: str) -> DashboardResponse:
    name, content_type = ASSETS[path]
    return DashboardResponse(status=OK, content_type=content_type, body=(PAGE_DATA / name).read_bytes())


def _answer_route(route: CommandRoute, runtime: Runtime) -> DashboardResponse:
    answer = run_routed_command(route, runtime)
    return DashboardResponse(status=answer.status, content_type=JSON, body=answer.document.encode())


def _answer_command(target: str, runtime: Runtime) -> DashboardResponse:
    route = route_command(target.removeprefix(API_PREFIX))
    if route is None:
        return _answer_error(NOT_FOUND, f"no route serves {target}")
    return _answer_route(route, runtime)


def _answer_change(target: str, runtime: Runtime) -> DashboardResponse:
    path = urlsplit(target).path
    route = None
    if path.startswith(API_PREFIX):
        route = route_change(target.removeprefix(API_PREFIX)) or route_action(path.removeprefix(API_PREFIX))
    if route is None:
        return _answer_error(NOT_FOUND, f"no route changes state at {target}")
    return _answer_route(route, runtime)


def _read_project(target: str) -> str | None:
    return next(iter(parse_qs(urlsplit(target).query).get(PROJECT_PARAMETER, ())), None)


def _select_project_answer(answer: CommandAnswer, project: str | None) -> CommandAnswer:
    document = select_project_rows(json.loads(answer.document), project)
    return CommandAnswer(status=answer.status, document=json.dumps(document))


def _answer_html(status: int, fragment: str) -> DashboardResponse:
    return DashboardResponse(status=status, content_type=HTML, body=fragment.encode())


def _answer_awawa_tab(target: str, dashboard: Dashboard) -> DashboardResponse | None:
    address = read_awawa_address(target)
    if address is None:
        return None
    asked = {name: address.read(name) for name in ADDON_PARAMETERS if address.read(name) is not None}
    query = asked | {VIEW_PARAMETER: asked.get(VIEW_PARAMETER, FIRST_AWAWA_VIEW)}
    answer = dashboard.addon.ask(address.project, query | {ADDON_FILTER: list(address.read_all(ADDON_FILTER))})
    return _answer_html(answer.status, render_awawa_tab(answer, address))


def _answer_view(target: str, dashboard: Dashboard, runtime: Runtime) -> DashboardResponse:
    project = _read_project(target)
    shown = target.removeprefix(VIEWS_PREFIX)
    if urlsplit(shown).path == ADDONS_REGION:
        return _answer_html(OK, render_addons_rail(dashboard.addon.list_projects(), project))
    tab = _answer_awawa_tab(shown, dashboard)
    if tab is not None:
        return tab
    selected = None if urlsplit(target.removeprefix(VIEWS_PREFIX)).path in REGION_ROUTES else project
    renderers = {
        **VIEW_RENDERERS,
        "heartbeat": lambda document: render_heartbeat(document, runtime.read_clock()),
        "selector": lambda document: render_project_selector(document, project),
    }
    view = route_view(target.removeprefix(VIEWS_PREFIX), renderers)
    if view is None:
        return _answer_error(NOT_FOUND, f"no view serves {target}")
    answers = {
        name: _select_project_answer(run_routed_command(route, runtime), selected)
        for name, route in view.routes.items()
    }
    answers.update(
        (name, _select_project_answer(run_routed_command(route, runtime), selected))
        for name, route in view.follow(answers).items()
    )
    status = next(iter(answers.values())).status
    return DashboardResponse(status=status, content_type=HTML, body=view.render(answers).encode())


def _answer_addon(target: str, dashboard: Dashboard) -> DashboardResponse:
    address = urlsplit(target)
    project = address.path.removeprefix(AWAWA_PREFIX)
    if not project or PATH_SEPARATOR in project:
        return _answer_error(NOT_FOUND, f"no route serves {target}")
    parameters = parse_qs(address.query)
    query = {name: parameters[name][0] for name in ADDON_PARAMETERS if name in parameters}
    answer = dashboard.addon.ask(project, query | {ADDON_FILTER: parameters.get(ADDON_FILTER, [])})
    return DashboardResponse(status=answer.status, content_type=JSON, body=json.dumps(answer.document).encode())


def _answer_reading(target: str, dashboard: Dashboard, runtime: Runtime) -> DashboardResponse:
    path = urlsplit(target).path
    if path == PAGE_PATH:
        return _answer_page(dashboard)
    if path in ASSETS:
        return _answer_asset(path)
    if path.startswith(AWAWA_PREFIX):
        return _answer_addon(target, dashboard)
    if path.startswith(API_PREFIX):
        return _answer_command(target, runtime)
    if path.startswith(VIEWS_PREFIX):
        return _answer_view(target, dashboard, runtime)
    return _answer_error(NOT_FOUND, f"nothing is served at {target}")


def answer_dashboard_request(incoming: IncomingRequest, dashboard: Dashboard, runtime: Runtime) -> DashboardResponse:
    refusal = _refuse(incoming, dashboard)
    if refusal is not None:
        return refusal
    if incoming.method == STATE_CHANGING_METHOD:
        return _answer_change(incoming.target, runtime)
    if incoming.method != READING_METHOD:
        return _answer_error(NOT_FOUND, f"no route serves the method {incoming.method}")
    return _answer_reading(incoming.target, dashboard, runtime)
