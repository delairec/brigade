SECTION_HEADING = "## Captures\n"
NEXT_HEADING = "\n## "


def replace_captures_section(body: str, section: str) -> str:
    start = body.find(SECTION_HEADING)
    if start < 0:
        return f"{body}\n{section}"
    end = body.find(NEXT_HEADING, start + len(SECTION_HEADING))
    following = "" if end < 0 else body[end:]
    return f"{body[:start]}{section}{following}"
