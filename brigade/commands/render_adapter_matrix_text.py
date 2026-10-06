from brigade.commands.adapter_matrix import CAPABILITIES

WORD_SEPARATOR = "_"
LABEL_SEPARATOR = " "
COLUMN_GAP = 2
LEGEND_TITLE = "fallbacks"
LEGEND_INDENT = "  "
ERROR_PREFIX = "error: "


def _label(key: str) -> str:
    return key.replace(WORD_SEPARATOR, LABEL_SEPARATOR)


HEADER = ("adapter", "audience", *(_label(capability) for capability in CAPABILITIES))


def _list_cells(row: dict) -> tuple[str, ...]:
    return (row["name"], _label(row["audience"]), *(row["capabilities"][capability] for capability in CAPABILITIES))


def _list_measured_cells(row: dict) -> tuple[str, ...]:
    if row["error"] is not None:
        return row["name"], _label(row["audience"])
    return _list_cells(row)


def _measure_columns(adapters: list[dict]) -> list[int]:
    rows = [HEADER, *(_list_measured_cells(row) for row in adapters)]
    return [max(len(cells[column]) for cells in rows if column < len(cells)) for column in range(len(HEADER))]


def _join_cells(cells: tuple[str, ...], widths: list[int]) -> str:
    padded = [f"{cell:<{width + COLUMN_GAP}}" for cell, width in zip(cells[:-1], widths)]
    return "".join([*padded, cells[-1]])


def _render_row(row: dict, widths: list[int]) -> str:
    if row["error"] is not None:
        return _join_cells((row["name"], _label(row["audience"]), f"{ERROR_PREFIX}{row['error']}"), widths)
    return _join_cells(_list_cells(row), widths)


def _render_legend(fallbacks: dict) -> list[str]:
    labels = {capability: f"no {_label(capability)}" for capability in fallbacks}
    width = max(len(label) for label in labels.values())
    return [
        LEGEND_TITLE,
        *(f"{LEGEND_INDENT}{labels[capability]:<{width + COLUMN_GAP}}{text}" for capability, text in fallbacks.items()),
    ]


def render_adapter_matrix_text(document: dict) -> str:
    widths = _measure_columns(document["adapters"])
    table = [_join_cells(HEADER, widths), *(_render_row(row, widths) for row in document["adapters"])]
    return "\n".join([*table, "", *_render_legend(document["fallbacks"])])
