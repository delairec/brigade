COLUMN_SEPARATOR = "  "


def _render_line(cells: tuple[str, ...], widths: list[int]) -> str:
    padded = [cell.ljust(width) for cell, width in zip(cells[:-1], widths, strict=True)]
    return COLUMN_SEPARATOR.join([*padded, cells[-1]])


def render_table(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    lines = [header, *rows]
    widths = [max(len(line[index]) for line in lines) for index in range(len(header) - 1)]
    return "\n".join(_render_line(line, widths) for line in lines)
