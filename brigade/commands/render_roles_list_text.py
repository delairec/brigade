SLOT_WIDTH = 9
ROLE_WIDTH = 12
SOURCE_WIDTH = 14
HEADER = {"slot": "slot", "role": "role", "source": "source", "model": "model"}
NO_MODEL = "-"


def _render_row(row: dict) -> str:
    model = NO_MODEL if row["model"] is None else row["model"]
    return f"{row['slot']:<{SLOT_WIDTH}}{row['role']:<{ROLE_WIDTH}}{row['source']:<{SOURCE_WIDTH}}{model}"


def render_roles_list_text(document: dict) -> str:
    return "\n".join(_render_row(row) for row in [HEADER, *document["roles"]])
