import re

from brigade.captures.describe_captures_section import TABLE_HEADING

CAPTURES_SECTION = re.compile(rf"## Captures\n.*?{re.escape(TABLE_HEADING)}(?:\|[^\n]*\n)*", re.DOTALL)
CHECKS_SECTION = re.compile(r"## Checks of [^\n]*\n\n(?:- [^\n]*\n)*\n")


def replace_captures_section(body: str, section: str) -> str:
    captured = CAPTURES_SECTION.search(body)
    if captured is not None:
        return f"{body[: captured.start()]}{section}{body[captured.end() :]}"
    checked = CHECKS_SECTION.search(body)
    if checked is not None:
        return f"{body[: checked.end()]}{section}\n{body[checked.end() :]}"
    return f"{body}\n{section}"
