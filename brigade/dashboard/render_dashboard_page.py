import re
from collections.abc import Callable

PAGE_PATH = "/"
STYLESHEET_PATH = "/dashboard.css"
STYLESHEET_LINK = f'<link rel="stylesheet" href="{STYLESHEET_PATH}">'
SCRIPT_TAG = '<script src="/dashboard.js" defer></script>'
EMPTY_VIEW = '<main id="view"></main>'
HOME_PAGE = "home"
HIDDEN_NEXT_TICK = '<section class="next-tick" hidden>'
SHOWN_NEXT_TICK = '<section class="next-tick">'
EMPTY_REGION = re.compile(r'(<(\w+)\b[^>]*\bdata-region="([^"]+)"[^>]*>)(</\2>)')
EMPTY_NEXT_TICK = re.compile(r'(<(\w+)\b[^>]*\bdata-next-tick="([^"]+)"[^>]*>)(</\2>)')


def render_dashboard_page(page: str, view: str, answer: Callable[[str], str]) -> str:
    def fill_region(region: re.Match) -> str:
        return f"{region.group(1)}{answer(region.group(3))}{region.group(4)}"

    shell = EMPTY_REGION.sub(fill_region, answer(PAGE_PATH))
    if page == HOME_PAGE:
        shell = EMPTY_NEXT_TICK.sub(fill_region, shell.replace(HIDDEN_NEXT_TICK, SHOWN_NEXT_TICK))
    return (
        shell.replace(STYLESHEET_LINK, f"<style>{answer(STYLESHEET_PATH)}</style>")
        .replace(SCRIPT_TAG, "")
        .replace(EMPTY_VIEW, f'<main id="view">{answer(view)}</main>')
    )
