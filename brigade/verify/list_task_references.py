import re

from brigade.corpus.read_entity import Entity

CITING_FIELDS = ("SPEC", "RATIONALE")
URL = re.compile(r"https?://\S+")
CLOSING_PUNCTUATION = ".,;:)"


def list_task_references(task: Entity) -> list[dict]:
    return [
        {"url": url.group().rstrip(CLOSING_PUNCTUATION), "field": field.name, "line": field.value}
        for field in task.fields
        if field.name in CITING_FIELDS
        for url in URL.finditer(field.value)
    ]
