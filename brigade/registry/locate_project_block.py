ENTITY_TYPE = "PROJECT"
INDENT = "\t"


def _belongs_to_block(line: str) -> bool:
    return line.startswith(INDENT) or not line.strip()


def locate_project_block(lines: list[str], name: str) -> range | None:
    header = f"{ENTITY_TYPE} {name}"
    for start, line in enumerate(lines):
        if line.rstrip() != header:
            continue
        end = start + 1
        while end < len(lines) and _belongs_to_block(lines[end]):
            end += 1
        return range(start, end)
    return None
