from brigade.registry.locate_project_block import locate_project_block


def remove_project_entity(text: str, name: str) -> str:
    lines = text.splitlines(keepends=True)
    block = locate_project_block(lines, name)
    if block is None:
        return text
    return "".join(lines[: block.start] + lines[block.stop :])
