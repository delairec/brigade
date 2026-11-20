from urllib.parse import parse_qsl, unquote, urlsplit

from brigade.dashboard.awawa_address import AwawaAddress

TAB_PREFIX = "awawa/"
PATH_SEPARATOR = "/"
PROJECT_PARAMETER = "project"


def read_awawa_address(target: str) -> AwawaAddress | None:
    address = urlsplit(target)
    if not address.path.startswith(TAB_PREFIX):
        return None
    project = address.path.removeprefix(TAB_PREFIX)
    if not project or PATH_SEPARATOR in project:
        return None
    parameters = tuple((name, value) for name, value in parse_qsl(address.query) if name != PROJECT_PARAMETER)
    return AwawaAddress(project=unquote(project), parameters=parameters)
