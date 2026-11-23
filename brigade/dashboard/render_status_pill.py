from brigade.dashboard.render_tone import render_tone


def render_status_pill(state: str, label: str = "") -> str:
    return f'<span class="pill">{render_tone(state, label)}</span>'
