from brigade.corpus.locate_entity_block import locate_entity_block

ENTITY_TYPE = "REQUEST"
STATUS_PREFIX = "\tSTATUS "
PLANNED_STATUS = "planned"
NO_PULL_REQUEST_LINE = ""


def _describe_pull_request(pr: int | None) -> str:
    if pr is None:
        return NO_PULL_REQUEST_LINE
    return f"\tPR {pr}\n"


def mark_request_planned(text: str, name: str, milestone: str, pr: int | None) -> str:
    lines = text.splitlines(keepends=True)
    for index in locate_entity_block(lines, ENTITY_TYPE, name):
        if lines[index].startswith(STATUS_PREFIX):
            lines[index] = f'{STATUS_PREFIX}{PLANNED_STATUS}\n\tMILESTONE "{milestone}"\n{_describe_pull_request(pr)}'
    return "".join(lines)
