import hmac
import json
from importlib.resources import files
from string import Template
from urllib.parse import urlsplit

from brigade.dashboard.dashboard_exchange import LOOPBACK_HOST, Dashboard, DashboardResponse, IncomingRequest
from brigade.dashboard.render_fragment import render_fragment
from brigade.dashboard.render_inbox_view import render_inbox_view
from brigade.dashboard.route_change import route_change
from brigade.dashboard.route_command import CommandRoute, route_command
from brigade.dashboard.run_routed_command import run_routed_command
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
VIEWS_PREFIX = "/views/"
READING_METHOD = "GET"
STATE_CHANGING_METHOD = "POST"
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
OK = 200
VIEW_RENDERERS = {"inbox": render_inbox_view}


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
    route = route_change(target.removeprefix(API_PREFIX))
    if route is None:
        return _answer_error(NOT_FOUND, f"no route changes state at {target}")
    return _answer_route(route, runtime)


def _answer_view(target: str, runtime: Runtime) -> DashboardResponse:
    view = target.removeprefix(VIEWS_PREFIX)
    route = route_command(view)
    if route is None:
        return _answer_error(NOT_FOUND, f"no view serves {target}")
    answer = run_routed_command(route, runtime)
    render = VIEW_RENDERERS.get(view, render_fragment) if answer.status == OK else render_fragment
    fragment = render(json.loads(answer.document))
    return DashboardResponse(status=answer.status, content_type=HTML, body=fragment.encode())


def _answer_reading(target: str, dashboard: Dashboard, runtime: Runtime) -> DashboardResponse:
    path = urlsplit(target).path
    if path == PAGE_PATH:
        return _answer_page(dashboard)
    if path in ASSETS:
        return _answer_asset(path)
    if path.startswith(API_PREFIX):
        return _answer_command(target, runtime)
    if path.startswith(VIEWS_PREFIX):
        return _answer_view(target, runtime)
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
