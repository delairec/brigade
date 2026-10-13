from brigade.corpus.locate_entity_block import locate_entity_block

ENTITY_TYPE = "PROJECT"
STATUS_PREFIX = "\tSTATUS "


def set_project_status(text: str, name: str, status: str) -> str | None:
    lines = text.splitlines(keepends=True)
    block = locate_entity_block(lines, ENTITY_TYPE, name)
    if block is None:
        return None
    for index in block:
        if lines[index].startswith(STATUS_PREFIX):
            lines[index] = f"{STATUS_PREFIX}{status}\n"
    return "".join(lines)
