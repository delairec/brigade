from dataclasses import dataclass

QUIET = "count num"
HOT = "count hot num"


@dataclass(frozen=True)
class RailDocuments:
    status: dict
    inbox: dict
    reports: dict


def _render_link(view: str, label: str, count: str, heat: str = QUIET) -> str:
    return f'<a href="#{view}">{label} <span class="{heat}">{count}</span></a>'


def render_rail(documents: RailDocuments) -> str:
    waves = len(documents.status["waves"])
    live_runs = len(documents.status["live_runs"])
    patterns = len(documents.inbox["patterns"])
    reports = len(documents.reports["reports"])
    inbox_heat = HOT if patterns else QUIET
    return (
        '<section class="rail-group"><h2>Operate</h2><a href="#status">Home</a>'
        f"{_render_link('waves', 'Waves', f'{waves} open')}"
        f"{_render_link('runs', 'Runs', f'{live_runs} live')}"
        f"{_render_link('inbox', 'Inbox', str(patterns), inbox_heat)}</section>"
        '<section class="rail-group"><h2>Understand</h2><a href="#ledger">Ledger</a>'
        f"{_render_link('reports', 'Reports', str(reports))}</section>"
    )
