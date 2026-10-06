def _render_once(document: dict) -> list[str]:
    return [f"tick {document['ts']}: {document['actions_applied']} actions applied in {document['duration_ms']} ms"]


def _render_dry_run(document: dict) -> list[str]:
    snapshot_lines = [f"  {key}  {value}" for key, value in document["snapshot"].items() if key != "schema_version"]
    plan_lines = [f"  {action}" for action in document["plan"]] or ["  no action"]
    return ["snapshot", *snapshot_lines, "plan", *plan_lines]


def _render_loop(document: dict) -> list[str]:
    return [f"tick --loop: {document['ticks']} ticks"]


RENDERERS = {"once": _render_once, "dry-run": _render_dry_run, "loop": _render_loop}


def render_tick_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["mode"]](document))
