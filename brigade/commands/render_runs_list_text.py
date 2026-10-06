COLUMN_SEPARATOR = "  "
ABSENT = "-"
NO_RUNS = "no runs"
COLUMNS = ("run", "procedure", "slot", "role", "project", "state", "outcome")


def _render_value(value) -> str:
    if value is None:
        return ABSENT
    return value


def render_runs_list_text(document: dict) -> str:
    if not document["runs"]:
        return NO_RUNS
    return "\n".join(
        COLUMN_SEPARATOR.join(_render_value(listed[column]) for column in COLUMNS) for listed in document["runs"]
    )
