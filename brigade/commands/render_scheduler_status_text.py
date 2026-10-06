def _describe_last_tick(last_tick) -> str:
    if last_tick is None:
        return "never"
    return f"{last_tick['ts']}, {last_tick['actions_applied']} actions applied in {last_tick['duration_ms']} ms"


def render_scheduler_status_text(document: dict) -> str:
    lines = [f"scheduler  {document['scheduler']}", *(f"unit       {unit}" for unit in document["unit_files"])]
    if document["cron_line"] is not None:
        lines.append(f"cron line  {document['cron_line']}")
    if document["next_activation"] is not None:
        lines.append(f"next       {document['next_activation']}")
    lines.append(f"last tick  {_describe_last_tick(document['last_tick'])}")
    return "\n".join(lines)
