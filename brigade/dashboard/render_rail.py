from dataclasses import dataclass

QUIET = "count num"
HOT = "count hot num"


@dataclass(frozen=True)
class RailDocuments:
    status: dict
    inbox: dict
    reports: dict


def _render_link(view: str, label: str, count: str, heat: str = QUIET) -> str:
    return f'<a href="#{view}" data-rail-view="{view}">{label} <span class="{heat}">{count}</span></a>'


def _render_plain_link(view: str, label: str) -> str:
    return f'<a href="#{view}" data-rail-view="{view}">{label}</a>'


def render_rail(documents: RailDocuments) -> str:
    waves = len(documents.status["waves"])
    live_runs = len(documents.status["live_runs"])
    patterns = len(documents.inbox["patterns"])
    reports = len(documents.reports["reports"])
    inbox_heat = HOT if patterns else QUIET
    return (
        f'<section class="rail-group"><h2>Operate</h2>{_render_plain_link("status", "Home")}'
        f"{_render_link('waves', 'Waves', f'{waves} open')}"
        f"{_render_link('runs', 'Runs', f'{live_runs} live')}"
        f"{_render_link('inbox', 'Inbox', str(patterns), inbox_heat)}</section>"
        f'<section class="rail-group"><h2>Understand</h2>{_render_plain_link("ledger", "Ledger")}'
        f"{_render_link('reports', 'Reports', str(reports))}</section>"
    )
