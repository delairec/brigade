from pathlib import Path

URL_MARK = "://"
URL_REFUSAL = "a REFERENCE is a repository path: the review cannot open a URL; copy the reference into the repository"


def _refuse(reference: str) -> str | None:
    if URL_MARK in reference:
        return URL_REFUSAL
    return None


def _list_slices(captures: Path, covers: str | None, side: str) -> list[str]:
    return [str(sliced) for sliced in sorted(captures.glob(f"{covers}-{side}-[0-9][0-9].png"))]


def _find_captures(covers: str | None, captures: Path) -> dict | None:
    delivered = _list_slices(captures, covers, "delivered")
    shown = _list_slices(captures, covers, "reference")
    if not (delivered and shown):
        return None
    return {"delivered": delivered, "reference": shown}


def describe_task_references(references: list[dict], captures: Path) -> list[dict]:
    return [
        {
            **reference,
            "refusal": _refuse(reference["reference"]),
            "captures": _find_captures(reference["covers"], captures),
        }
        for reference in references
    ]
