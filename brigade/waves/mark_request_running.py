from brigade.corpus.locate_entity_block import locate_entity_block
from brigade.waves.read_wave_request import ENTITY_TYPE

STATUS_PREFIX = "\tSTATUS "
RUNNING_STATUS = "running"


def mark_request_running(text: str, name: str) -> str:
    lines = text.splitlines(keepends=True)
    for index in locate_entity_block(lines, ENTITY_TYPE, name):
        if lines[index].startswith(STATUS_PREFIX):
            lines[index] = f"{STATUS_PREFIX}{RUNNING_STATUS}\n"
    return "".join(lines)
