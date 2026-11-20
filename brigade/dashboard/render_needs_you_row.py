from dataclasses import dataclass
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone


@dataclass(frozen=True)
class NeedsYou:
    subject: str
    reason: str
    command: str
    age_s: int | None = None
    mark: str = ""
    state: str = ""
    link: tuple[str, str] | None = None


def _render_act(row: NeedsYou) -> str:
    if row.link is None:
        return f'<code class="cmd">{escape(row.command)}</code>'
    label, href = row.link
    return f'<a class="btn btn-primary" href="{escape(href)}">{escape(label)}</a>'


def render_needs_you_row(row: NeedsYou) -> str:
    return (
        f'<li class="needs-you tone-{read_state_tone(row.state)}"><span class="mark">{escape(row.mark)}</span>'
        f"<div><h3>{escape(row.subject)}</h3><p>{escape(row.reason)}</p></div>"
        f'<div class="act">{_render_act(row)}</div></li>'
    )
