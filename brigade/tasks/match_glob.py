import re

WILDCARDS = re.compile(r"(\*\*|\*)")
TRANSLATIONS = {"**": ".*", "*": "[^/]*"}


def match_glob(pattern: str, path: str) -> bool:
    expression = "".join(TRANSLATIONS.get(part, re.escape(part)) for part in WILDCARDS.split(pattern))
    return re.fullmatch(expression, path) is not None
