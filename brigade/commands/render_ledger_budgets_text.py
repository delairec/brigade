from brigade.commands.format_steps_line import format_steps_line

ESTIMATE_MARK = "  estimate"


def render_ledger_budgets_text(document: dict) -> str:
    procedures = document["procedures"]
    width = max((len(name) for name in procedures), default=0)
    lines = [f"steps over the last {document['last']} runs finished of each procedure:"]
    for name, summary in procedures.items():
        lines.append(format_steps_line(name, width, summary) + (ESTIMATE_MARK if summary["estimate"] else ""))
    return "\n".join(lines)
