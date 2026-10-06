def render_runs_logs_text(document: dict) -> str:
    return "\n".join(document["lines"])
