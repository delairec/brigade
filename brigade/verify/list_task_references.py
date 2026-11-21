from brigade.corpus.decode_atom import decode_atom

REFERENCE_FIELD = "REFERENCE"


def _read_covers(reference: dict) -> str | None:
    covers = [decode_atom(field["atoms"][0]) for field in reference["fields"]]
    return covers[0] if covers else None


def list_task_references(task: dict) -> list[dict]:
    return [
        {"reference": decode_atom(field["atoms"][0]), "covers": _read_covers(field)}
        for field in task["fields"]
        if field["name"] == REFERENCE_FIELD
    ]
