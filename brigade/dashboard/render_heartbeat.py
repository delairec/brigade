from datetime import datetime
from html import escape

SECONDS_PER_MINUTE = 60
STALE = ' <strong class="heartbeat-stale">stale</strong>'


def _describe_last_tick(last_tick: dict | None, now: datetime) -> str:
    if last_tick is None:
        return "No tick recorded yet"
    ts = escape(last_tick["ts"])
    minutes = int((now - datetime.fromisoformat(last_tick["ts"])).total_seconds() // SECONDS_PER_MINUTE)
    return f'Last tick <time datetime="{ts}">{ts}</time>, {minutes} min ago'


def render_heartbeat(document: dict, now: datetime) -> str:
    stale = STALE if document["stale"] else ""
    return f'<p class="heartbeat">{_describe_last_tick(document["last_tick"], now)}{stale}</p>'
