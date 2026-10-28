from dataclasses import dataclass

LOOPBACK_HOST = "127.0.0.1"


@dataclass(frozen=True)
class Dashboard:
    port: int
    token: str

    @property
    def origin(self) -> str:
        return f"http://{LOOPBACK_HOST}:{self.port}"

    @property
    def url(self) -> str:
        return f"{self.origin}/"


@dataclass(frozen=True)
class IncomingRequest:
    method: str
    target: str
    host: str | None
    origin: str | None = None
    token: str | None = None


@dataclass(frozen=True)
class DashboardResponse:
    status: int
    content_type: str
    body: bytes
