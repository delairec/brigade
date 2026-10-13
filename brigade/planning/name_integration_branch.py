import re

BRANCH_PREFIX = "integration/"
SEPARATOR_RUN = re.compile(r"[\W_]+")
HYPHEN = "-"


def name_integration_branch(milestone: str, title: str) -> str:
    return f"{BRANCH_PREFIX}{milestone}-{SEPARATOR_RUN.sub(HYPHEN, title.lower())}"
