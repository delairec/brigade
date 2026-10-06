SINGLE_SEGMENT = 1


def _name_segments(count: int) -> str:
    if count == SINGLE_SEGMENT:
        return f"{count} segment"
    return f"{count} segments"


def render_run_text(document: dict) -> str:
    if "outcome" not in document:
        return document["run"]
    return (
        f"run {document['run']}: {document['procedure']} as {document['role']} ({document['slot']})"
        f" {document['outcome']} after {_name_segments(document['segments'])}"
    )
