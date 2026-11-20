PROJECT_FIELD = "project"
NAMING_FIELDS = {"projects": "name"}


def _belongs(row: object, project: str, key: str | None) -> bool:
    if not isinstance(row, dict):
        return True
    field = PROJECT_FIELD if PROJECT_FIELD in row else NAMING_FIELDS.get(key)
    return field is None or row.get(field) in (None, project)


def _select(value: object, project: str, key: str | None) -> object:
    if isinstance(value, dict):
        return {name: _select(item, project, name) for name, item in value.items()}
    if isinstance(value, list):
        return [row for row in value if _belongs(row, project, key)]
    return value


def select_project_rows(document: dict, project: str | None) -> dict:
    if project is None:
        return document
    return {name: _select(item, project, name) for name, item in document.items()}
