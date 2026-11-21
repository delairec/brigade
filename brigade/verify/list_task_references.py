from brigade.corpus.decode_atom import decode_atom

REFERENCE_FIELD = "REFERENCE"
COVERS_FIELD = "COVERS"


def _read_covers(reference: dict) -> str | None:
    covers = [decode_atom(field["atoms"][0]) for field in reference["fields"] if field["name"] == COVERS_FIELD]
    return covers[0] if covers else None


def list_task_references(task: dict) -> list[dict]:
    return [
        {"reference": decode_atom(field["atoms"][0]), "covers": _read_covers(field)}
        for field in task["fields"]
        if field["name"] == REFERENCE_FIELD
    ]
