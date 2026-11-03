import re

SEPARATOR_RUN = re.compile(r"[^a-z0-9]+")
SLUG_LENGTH = 40
SLUG_SEPARATOR = "-"
PREFIX_OF_TYPE = {"feat": "feature"}


def name_task_branch(task_type: str, task: str, title: str) -> str:
    return f"{PREFIX_OF_TYPE.get(task_type, task_type)}/{task}-{_slug_title(title)}"


def _slug_title(title: str) -> str:
    slug = SEPARATOR_RUN.sub(SLUG_SEPARATOR, title.lower()).strip(SLUG_SEPARATOR)
    if len(slug) <= SLUG_LENGTH:
        return slug
    cut = slug.rfind(SLUG_SEPARATOR, 0, SLUG_LENGTH)
    return slug[:SLUG_LENGTH] if cut == -1 else slug[:cut]
