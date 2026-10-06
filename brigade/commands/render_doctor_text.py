STATE_WIDTH = 9
NAME_WIDTH = 13
DETAIL_WIDTH = 36


def _render_prerequisite(item: dict) -> str:
    return f"{item['state']:<{STATE_WIDTH}}{item['name']:<{NAME_WIDTH}}{item['detail']}"


def _render_optional(item: dict) -> str:
    label = "else" if item["state"] == "ok" else "fallback"
    columns = f"{item['state']:<{STATE_WIDTH}}{item['name']:<{NAME_WIDTH}}{item['detail']:<{DETAIL_WIDTH - 1}}"
    return f"{columns} {label}: {item['fallback']}"


def _summarise(prerequisites: list[dict], optional_items: list[dict]) -> str:
    prerequisites_ok = sum(1 for item in prerequisites if item["state"] == "ok")
    on_fallback = sum(1 for item in optional_items if item["state"] != "ok")
    optional_phrase = "optional item on its fallback" if on_fallback == 1 else "optional items on their fallback"
    return f"doctor: {prerequisites_ok} of {len(prerequisites)} prerequisites ok · {on_fallback} {optional_phrase}"


def render_doctor_text(document: dict) -> str:
    prerequisites = [item for item in document["items"] if item["kind"] == "prerequisite"]
    optional_items = [item for item in document["items"] if item["kind"] == "optional"]
    lines = [
        "prerequisites",
        *(_render_prerequisite(item) for item in prerequisites),
        "optional",
        *(_render_optional(item) for item in optional_items),
        "",
        _summarise(prerequisites, optional_items),
    ]
    return "\n".join(lines)
