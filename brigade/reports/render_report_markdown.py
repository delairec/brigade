from brigade.reports.manual_test_tables import MANUAL_TEST_HEADER, MANUAL_TEST_TABLES

CELL_SEPARATOR = "|"


def _render_row(cells: tuple[str, ...]) -> str:
    escaped = (cell.replace(CELL_SEPARATOR, f"\\{CELL_SEPARATOR}") for cell in cells)
    return f"| {' | '.join(escaped)} |\n"


def _render_table(heading: str, values: list[str]) -> str:
    rows = "".join(_render_row((str(rank), value)) for rank, value in enumerate(values, start=1))
    rule = _render_row(tuple("---" for _ in MANUAL_TEST_HEADER))
    return f"\n## {heading}\n\n{_render_row(MANUAL_TEST_HEADER)}{rule}{rows}"


def render_report_markdown(entity: dict) -> str:
    fields = entity["fields"]
    listed = "".join(
        f"- {field['name']}: {field['value']}\n" for field in fields if field["name"] not in MANUAL_TEST_TABLES
    )
    tables = "".join(
        _render_table(heading, values)
        for name, heading in MANUAL_TEST_TABLES.items()
        if (values := [field["value"] for field in fields if field["name"] == name])
    )
    return f"# {entity['type']} {entity['name']}\n\n{listed}{tables}"
