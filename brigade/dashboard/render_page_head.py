from dataclasses import dataclass
from html import escape

from brigade.dashboard.poll_interval import POLL_INTERVAL_S
from brigade.dashboard.render_status_pill import render_status_pill

FRESH = f'<p class="fresh num" data-fresh>refreshes every {POLL_INTERVAL_S} s</p>'


@dataclass(frozen=True)
class Crumb:
    label: str
    address: str


@dataclass(frozen=True)
class PageHead:
    title: str
    lede: str
    name: str = ""
    state: str = ""
    crumbs: tuple[Crumb, ...] = ()
    fresh: str = ""
    pill: str = ""
    caption: str = ""


def _render_title(head: PageHead) -> str:
    if not head.name:
        return escape(head.title)
    named = f'{escape(head.title)} <span class="mono">{escape(head.name)}</span>'
    if head.caption:
        named = f"{named} · {escape(head.caption)}"
    if head.pill:
        return f"{named} {head.pill}"
    if not head.state:
        return named
    return f"{named} {render_status_pill(head.state)}"


def _render_crumb(crumb: Crumb) -> str:
    if not crumb.address:
        return escape(crumb.label)
    return f'<a href="{escape(crumb.address)}">{escape(crumb.label)}</a>'


def _render_crumbs(head: PageHead) -> str:
    if not head.crumbs:
        return ""
    return f'<p class="crumbs">{" / ".join(_render_crumb(crumb) for crumb in head.crumbs)}</p>'


def render_page_head(head: PageHead) -> str:
    return (
        f'<header class="page-head"><div>{_render_crumbs(head)}<h1>{_render_title(head)}</h1>'
        f'<p class="lede">{escape(head.lede)}</p></div>{head.fresh or FRESH}</header>'
    )
