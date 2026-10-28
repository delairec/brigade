from urllib.parse import parse_qs, urlsplit

from brigade.dashboard.route_command import OPTION_PREFIX, PATH_SEPARATOR, CommandRoute, Listing

KIND_PARAMETER = "kind"
INBOX_LIST = ("inbox", "list", "--json")
PATTERN_LISTING = Listing(arguments=INBOX_LIST, names=(("patterns", "name"),))
PATTERN_OR_SIGNAL_LISTING = Listing(arguments=INBOX_LIST, names=(("patterns", "name"), ("signals", "id")))


def _route_ratification(pattern: str, query: dict) -> CommandRoute:
    kinds = tuple(f"--{KIND_PARAMETER}={kind}" for kind in query.get(KIND_PARAMETER, ()))
    return CommandRoute(
        arguments=("inbox", "ratify", *kinds, "--json", pattern), identifier=pattern, listing=PATTERN_LISTING
    )


def _route_dismissal(identifier: str, query: dict) -> CommandRoute:
    return CommandRoute(
        arguments=("inbox", "dismiss", "--json", identifier), identifier=identifier, listing=PATTERN_OR_SIGNAL_LISTING
    )


ROUTES = {("inbox", "ratify"): _route_ratification, ("inbox", "dismiss"): _route_dismissal}


def route_change(target: str) -> CommandRoute | None:
    address = urlsplit(target)
    *action, identifier = address.path.split(PATH_SEPARATOR)
    route = ROUTES.get(tuple(action))
    if route is None or not identifier or identifier.startswith(OPTION_PREFIX):
        return None
    return route(identifier, parse_qs(address.query))
