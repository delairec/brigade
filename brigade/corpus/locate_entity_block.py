INDENT = "\t"


def _belongs_to_block(line: str) -> bool:
    return line.startswith(INDENT) or not line.strip()


def locate_entity_block(lines: list[str], entity_type: str, name: str) -> range | None:
    header = f"{entity_type} {name}"
    start = next((index for index, line in enumerate(lines) if line.rstrip() == header), None)
    if start is None:
        return None
    end = start + 1
    while end < len(lines) and _belongs_to_block(lines[end]):
        end += 1
    return range(start, end)
