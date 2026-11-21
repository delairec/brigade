import re
from collections.abc import Callable

PAGE_PATH = "/"
STYLESHEET_PATH = "/dashboard.css"
STYLESHEET_LINK = f'<link rel="stylesheet" href="{STYLESHEET_PATH}">'
SCRIPT_TAG = '<script src="/dashboard.js" defer></script>'
EMPTY_VIEW = '<main id="view"></main>'
VIEWS_PREFIX = "/views/"
PAGE_VIEWS = {"home": "status"}
EMPTY_REGION = re.compile(r'(<(\w+)\b[^>]*\bdata-region="([^"]+)"[^>]*>)(</\2>)')


def render_dashboard_page(page: str, answer: Callable[[str], str]) -> str:
    def fill_region(region: re.Match) -> str:
        return f"{region.group(1)}{answer(region.group(3))}{region.group(4)}"

    shell = EMPTY_REGION.sub(fill_region, answer(PAGE_PATH))
    view = answer(f"{VIEWS_PREFIX}{PAGE_VIEWS.get(page, page)}")
    return (
        shell.replace(STYLESHEET_LINK, f"<style>{answer(STYLESHEET_PATH)}</style>")
        .replace(SCRIPT_TAG, "")
        .replace(EMPTY_VIEW, f'<main id="view">{view}</main>')
    )
