from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class NeedsYou:
    subject: str
    reason: str
    command: str


def render_needs_you_row(row: NeedsYou) -> str:
    return (
        f'<li class="needs-you"><span class="needs-you-subject">{escape(row.subject)}</span>'
        f'<span class="needs-you-reason">{escape(row.reason)}</span>'
        f'<code class="needs-you-action">{escape(row.command)}</code></li>'
    )
