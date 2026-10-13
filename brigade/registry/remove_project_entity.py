from brigade.corpus.locate_entity_block import locate_entity_block

ENTITY_TYPE = "PROJECT"


def remove_project_entity(text: str, name: str) -> str:
    lines = text.splitlines(keepends=True)
    block = locate_entity_block(lines, ENTITY_TYPE, name)
    if block is None:
        return text
    return "".join(lines[: block.start] + lines[block.stop :])
