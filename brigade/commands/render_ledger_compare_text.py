from brigade.commands.format_steps_line import format_steps_line

MEASURE_LABELS = {
    "steps": "steps",
    "steps_to_first_edit": "steps to first edit",
    "oversized_output_steps": "oversized output steps",
}
LABEL_WIDTH = max(len(label) for label in MEASURE_LABELS.values())
NOT_REPORTED = "not reported"


def _render_measure(label: str, summary) -> str:
    if summary is None:
        return f"  {label:<{LABEL_WIDTH}}  {NOT_REPORTED}"
    return format_steps_line(label, LABEL_WIDTH, summary)


def _render_period(heading: str, period: dict) -> list[str]:
    return [
        f"{heading}: {period['runs']} runs finished",
        *(_render_measure(label, period[measure]) for measure, label in MEASURE_LABELS.items()),
    ]


def render_ledger_compare_text(document: dict) -> str:
    day = document["before"]
    periods = document["periods"]
    return "\n".join(
        [*_render_period(f"before {day}", periods["before"]), *_render_period(f"from {day}", periods["from"])]
    )
