PAST_TENSES = {"paused": "paused", "active": "resumed"}


def render_project_status_text(document: dict) -> str:
    target = f"@PROJECT.{document['project']}"
    if document["changed"]:
        return f"{PAST_TENSES[document['status']]} {target}"
    return f"{target} is already {document['status']}"
