from pathlib import Path

URL_MARK = "://"
URL_REFUSAL = "a REFERENCE is a repository path: the review cannot open a URL; copy the reference into the repository"


def _refuse(reference: str) -> str | None:
    if URL_MARK in reference:
        return URL_REFUSAL
    return None


def _find_captures(covers: str | None, captures: Path) -> dict | None:
    delivered = captures / f"{covers}-delivered.png"
    shown = captures / f"{covers}-reference.png"
    if not (delivered.is_file() and shown.is_file()):
        return None
    return {"delivered": str(delivered), "reference": str(shown)}


def describe_task_references(references: list[dict], captures: Path) -> list[dict]:
    return [
        {
            **reference,
            "refusal": _refuse(reference["reference"]),
            "captures": _find_captures(reference["covers"], captures),
        }
        for reference in references
    ]
