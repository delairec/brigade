from brigade.corpus.decode_atom import decode_atom

REFERENCE_FIELD = "REFERENCE"
COVERS_FIELD = "COVERS"
REVISES_FIELD = "REVISES"
READ_FIELD = "READ"


def _read_nested(reference: dict, name: str) -> str | None:
    return next((decode_atom(field["atoms"][0]) for field in reference["fields"] if field["name"] == name), None)


def list_task_references(task: dict) -> list[dict]:
    return [
        {
            "reference": decode_atom(field["atoms"][0]),
            "covers": _read_nested(field, COVERS_FIELD),
            "revises": _read_nested(field, REVISES_FIELD),
            "reads": _read_nested(field, READ_FIELD),
        }
        for field in task["fields"]
        if field["name"] == REFERENCE_FIELD
    ]
