from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Fold:
    summary: str
    detail: str
    body: str
    opened: bool = False


def render_fold(fold: Fold) -> str:
    opened = " open" if fold.opened else ""
    detail = f" <span>· {escape(fold.detail)}</span>" if fold.detail else ""
    return f'<details class="fold"{opened}><summary>{escape(fold.summary)}{detail}</summary>{fold.body}</details>'
