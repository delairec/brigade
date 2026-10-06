STATE_WIDTH = 9
NAME_WIDTH = 13
STATES = ("created", "present", "differs")


def _render_item(item: dict) -> str:
    return f"{item['state']:<{STATE_WIDTH}}{item['name']:<{NAME_WIDTH}}{item['path']}"


def _summarise(items: list[dict]) -> str:
    counts = " · ".join(f"{state} {sum(1 for item in items if item['state'] == state)}" for state in STATES)
    return f"init: {counts}"


def _warn(item: dict) -> str:
    return f"warning: {item['name']} differs from the shipped file and is left as it is"


def render_init_text(document: dict) -> str:
    items = document["items"]
    lines = [
        *(_render_item(item) for item in items),
        "",
        _summarise(items),
        *(_warn(item) for item in items if item["state"] == "differs"),
    ]
    return "\n".join(lines)
