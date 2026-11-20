from html import escape

ACTION_FIELD = "action"
NOTHING_DECIDED = '<p class="next-tick-empty">the next tick decides nothing</p>'


def _describe_decision(decision: dict) -> str:
    fields = (f"{name} {value}" for name, value in decision.items() if name != ACTION_FIELD)
    return f"<li>{escape(', '.join(fields))}</li>"


def render_next_tick(document: dict) -> str:
    groups: dict[str, list[str]] = {}
    for decision in document["decisions"]:
        groups.setdefault(decision[ACTION_FIELD], []).append(_describe_decision(decision))
    rendered = "".join(f"<h3>{escape(action)}</h3><ul>{''.join(items)}</ul>" for action, items in groups.items())
    return rendered or NOTHING_DECIDED
