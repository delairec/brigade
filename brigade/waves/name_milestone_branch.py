import re

MILESTONE_BRANCH_PREFIX = "integration/"
SEPARATOR_RUN = re.compile(r"[^a-z0-9]+")


def name_milestone_branch(title: str) -> str:
    return f"{MILESTONE_BRANCH_PREFIX}{SEPARATOR_RUN.sub('-', title.lower()).strip('-')}"
