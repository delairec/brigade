import contextlib
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from brigade.dashboard.answer_dashboard_request import answer_dashboard_request
from brigade.dashboard.dashboard_exchange import LOOPBACK_HOST, Dashboard, IncomingRequest
from brigade.errors import BrigadeError
from brigade.runtime import Runtime

SECURITY_POLICY = "default-src 'self'"
GUARD_HEADER = "X-Brigade-Token"


class _DashboardServer(ThreadingHTTPServer):
    dashboard: Dashboard
    runtime: Runtime


class _DashboardHandler(BaseHTTPRequestHandler):
    server: _DashboardServer
    default_request_version = "HTTP/1.0"

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", SECURITY_POLICY)
        super().end_headers()

    def do_GET(self) -> None:
        self._answer()

    def do_POST(self) -> None:
        self._answer()

    def _answer(self) -> None:
        incoming = IncomingRequest(
            method=self.command,
            target=self.path,
            host=self.headers.get("Host"),
            origin=self.headers.get("Origin"),
            token=self.headers.get(GUARD_HEADER),
        )
        response = answer_dashboard_request(incoming, self.server.dashboard, self.server.runtime)
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)


def _listen(port: int) -> _DashboardServer:
    try:
        return _DashboardServer((LOOPBACK_HOST, port), _DashboardHandler)
    except OSError as error:
        raise BrigadeError(f"cannot listen on port {port}: {error.strerror}") from None


@contextlib.contextmanager
def start_dashboard(port: int, token: str, runtime: Runtime) -> Iterator[Dashboard]:
    server = _listen(port)
    server.dashboard = Dashboard(port=server.server_address[1], token=token)
    server.runtime = runtime
    serving = threading.Thread(target=server.serve_forever)
    serving.start()
    try:
        yield server.dashboard
    finally:
        server.shutdown()
        serving.join()
        server.server_close()
