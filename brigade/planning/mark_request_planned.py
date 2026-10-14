from brigade.corpus.locate_entity_block import locate_entity_block

ENTITY_TYPE = "REQUEST"
STATUS_PREFIX = "\tSTATUS "
PLANNED_STATUS = "planned"


def mark_request_planned(text: str, name: str, milestone: str, branch: str) -> str:
    lines = text.splitlines(keepends=True)
    for index in locate_entity_block(lines, ENTITY_TYPE, name):
        if lines[index].startswith(STATUS_PREFIX):
            lines[index] = f'{STATUS_PREFIX}{PLANNED_STATUS}\n\tMILESTONE "{milestone}"\n\tBRANCH "{branch}"\n'
    return "".join(lines)
