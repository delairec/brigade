import re
from dataclasses import dataclass
from urllib.parse import urlsplit

GITHUB_HOST = "github.com"
GITHUB_FORGE = "github"
NO_FORGE = "none"
URL_SCHEME_SEPARATOR = "://"
SCP_LIKE = re.compile(r"^(?:[^@/]+@)?(?P<host>[^:/]+):(?P<path>.*)$")
GIT_SUFFIX = ".git"


@dataclass(frozen=True)
class RemoteDescription:
    remote: str | None
    forge: str


def _split_host(url: str) -> tuple[str | None, str]:
    if URL_SCHEME_SEPARATOR in url:
        parts = urlsplit(url)
        return parts.hostname, parts.path
    scp_like = SCP_LIKE.match(url)
    if scp_like is not None:
        return scp_like["host"], scp_like["path"]
    return None, url


def describe_remote(url: str | None) -> RemoteDescription:
    if url is None:
        return RemoteDescription(remote=None, forge=NO_FORGE)
    host, path = _split_host(url)
    segments = [segment for segment in path.split("/") if segment]
    remote = "/".join(segments[-2:]).removesuffix(GIT_SUFFIX)
    return RemoteDescription(remote=remote or None, forge=GITHUB_FORGE if host == GITHUB_HOST else NO_FORGE)
