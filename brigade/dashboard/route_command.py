from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

OPTION_PREFIX = "-"
PATH_SEPARATOR = "/"
REF_PARAMETER = "ref"


@dataclass(frozen=True)
class Listing:
    arguments: tuple[str, ...]
    names: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CommandRoute:
    arguments: tuple[str, ...]
    identifier: str | None = None
    listing: Listing | None = None


WAVE_LISTING = Listing(arguments=("wave", "list", "--json"), names=(("waves", "wave"),))
PROJECT_LISTING = Listing(arguments=("project", "list", "--json"), names=(("projects", "name"),))
REPORT_LISTING = Listing(arguments=("reports", "list", "--json"), names=(("reports", "id"),))
ROUTES_WITHOUT_IDENTIFIER = {
    "waves": CommandRoute(arguments=WAVE_LISTING.arguments),
    "inbox": CommandRoute(arguments=("inbox", "list", "--json")),
    "ledger": CommandRoute(arguments=("ledger", "--json")),
    "reports": CommandRoute(arguments=REPORT_LISTING.arguments),
}


def _route_wave(wave: str, query: dict) -> CommandRoute:
    return CommandRoute(arguments=("wave", "show", "--json", wave), identifier=wave, listing=WAVE_LISTING)


def _route_corpus(project: str, query: dict) -> CommandRoute:
    references = tuple(f"--{REF_PARAMETER}={ref}" for ref in query.get(REF_PARAMETER, ()))
    return CommandRoute(
        arguments=("corpus", *references, "--json", project), identifier=project, listing=PROJECT_LISTING
    )


def _route_report(report: str, query: dict) -> CommandRoute:
    return CommandRoute(arguments=("reports", "show", "--json", report), identifier=report, listing=REPORT_LISTING)


ROUTES_WITH_IDENTIFIER = {"waves": _route_wave, "corpus": _route_corpus, "reports": _route_report}


def route_command(target: str) -> CommandRoute | None:
    address = urlsplit(target)
    segments = address.path.split(PATH_SEPARATOR)
    if len(segments) == 1:
        return ROUTES_WITHOUT_IDENTIFIER.get(segments[0])
    collection, identifier = segments if len(segments) == 2 else (None, None)
    if collection not in ROUTES_WITH_IDENTIFIER or not identifier or identifier.startswith(OPTION_PREFIX):
        return None
    return ROUTES_WITH_IDENTIFIER[collection](identifier, parse_qs(address.query))
