from brigade.registry.locate_project_block import locate_project_block

STATUS_PREFIX = "\tSTATUS "


def set_project_status(text: str, name: str, status: str) -> str | None:
    lines = text.splitlines(keepends=True)
    block = locate_project_block(lines, name)
    if block is None:
        return None
    for index in block:
        if lines[index].startswith(STATUS_PREFIX):
            lines[index] = f"{STATUS_PREFIX}{status}\n"
    return "".join(lines)
