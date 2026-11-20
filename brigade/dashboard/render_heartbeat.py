from datetime import datetime
from html import escape

SECONDS_PER_MINUTE = 60
MILLISECONDS_PER_SECOND = 1000
NO_TICK = '<p class="heartbeat"><span><span class="dot tone-off"></span><b>No tick recorded yet</b></span></p>'


def _render_liveness(document: dict) -> str:
    tone, word = ("failed", "stale") if document["stale"] else ("done", "alive")
    return f'<span><span class="dot tone-{tone}"></span><b>Tick {word}</b></span>'


def _render_last_tick(last_tick: dict, now: datetime) -> str:
    ts = escape(last_tick["ts"])
    ticked_at = datetime.fromisoformat(last_tick["ts"])
    minutes = int((now - ticked_at).total_seconds() // SECONDS_PER_MINUTE)
    return (
        f'<span class="num">last <time datetime="{ts}">{ticked_at:%H:%M:%SZ}</time>, {minutes} min ago</span>'
        f'<span class="num">{last_tick["duration_ms"] / MILLISECONDS_PER_SECOND:.1f} s'
        f" · {last_tick['actions_applied']} actions</span>"
    )


def render_heartbeat(document: dict, now: datetime) -> str:
    last_tick = document["last_tick"]
    if last_tick is None:
        return NO_TICK
    return f'<p class="heartbeat">{_render_liveness(document)}{_render_last_tick(last_tick, now)}</p>'
