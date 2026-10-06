from brigade.commands.adapter_matrix import CAPABILITIES

AUDIENCE_TITLES = {"supported_client": "Supported client", "test_suite": "Test-suite adapter"}
FALLBACKS_TITLE = "Fallbacks:"
ERROR_PREFIX = "error: "
CELL_SEPARATOR = "|"
ESCAPED_CELL_SEPARATOR = "\\|"
HEADER_RULE = "---"
EMPTY_CELL = ""
WORD_SEPARATOR = "_"
LABEL_SEPARATOR = " "


def _label(capability: str) -> str:
    return capability.replace(WORD_SEPARATOR, LABEL_SEPARATOR)


def _join_cells(cells: list[str]) -> str:
    return f"| {' | '.join(cells)} |"


def _list_cells(row: dict) -> list[str]:
    if row["error"] is not None:
        message = row["error"].replace(CELL_SEPARATOR, ESCAPED_CELL_SEPARATOR)
        return [row["name"], f"{ERROR_PREFIX}{message}", *([EMPTY_CELL] * (len(CAPABILITIES) - 1))]
    return [row["name"], *(row["capabilities"][capability] for capability in CAPABILITIES)]


def _render_table(audience: str, adapters: list[dict]) -> str:
    header = [AUDIENCE_TITLES[audience], *(_label(capability).capitalize() for capability in CAPABILITIES)]
    rows = [_list_cells(row) for row in adapters if row["audience"] == audience]
    return "\n".join(_join_cells(cells) for cells in [header, [HEADER_RULE] * len(header), *rows])


def render_adapter_matrix_markdown(document: dict) -> str:
    tables = [_render_table(audience, document["adapters"]) for audience in AUDIENCE_TITLES]
    legend = "\n".join(f"- no {_label(capability)}: {text}" for capability, text in document["fallbacks"].items())
    return "\n\n".join([*tables, FALLBACKS_TITLE, legend])
