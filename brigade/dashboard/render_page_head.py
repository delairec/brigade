from dataclasses import dataclass
from html import escape

from brigade.dashboard.render_status_pill import render_status_pill

FRESH = '<p class="fresh num" data-fresh>refreshes every 5 s</p>'


@dataclass(frozen=True)
class PageHead:
    title: str
    lede: str
    name: str = ""
    state: str = ""


def _render_title(head: PageHead) -> str:
    if not head.name:
        return escape(head.title)
    named = f'{escape(head.title)} <span class="mono">{escape(head.name)}</span>'
    if not head.state:
        return named
    return f"{named} {render_status_pill(head.state)}"


def render_page_head(head: PageHead) -> str:
    return (
        f'<header class="page-head"><div><h1>{_render_title(head)}</h1>'
        f'<p class="lede">{escape(head.lede)}</p></div>{FRESH}</header>'
    )
