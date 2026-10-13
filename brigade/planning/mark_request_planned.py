from brigade.corpus.locate_entity_block import locate_entity_block

ENTITY_TYPE = "REQUEST"
STATUS_PREFIX = "\tSTATUS "
PLANNED_STATUS = "planned"


def mark_request_planned(text: str, name: str, milestone: str, branch: str) -> str | None:
    lines = text.splitlines(keepends=True)
    block = locate_entity_block(lines, ENTITY_TYPE, name)
    if block is None:
        return None
    for index in block:
        if lines[index].startswith(STATUS_PREFIX):
            lines[index] = f'{STATUS_PREFIX}{PLANNED_STATUS}\n\tMILESTONE "{milestone}"\n\tBRANCH "{branch}"\n'
    return "".join(lines)
