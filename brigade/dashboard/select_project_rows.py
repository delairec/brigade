PROJECT_FIELD = "project"


def _belongs(row: object, project: str) -> bool:
    return not isinstance(row, dict) or row.get(PROJECT_FIELD, project) == project


def select_project_rows(document: dict, project: str | None) -> dict:
    if project is None:
        return document
    return {
        key: [row for row in value if _belongs(row, project)] if isinstance(value, list) else value
        for key, value in document.items()
    }
