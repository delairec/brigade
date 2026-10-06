FIELD_NAME_WIDTH = 6
TREE_FIELDS = ("ref", "sha", "kind", "root")


def render_corpus_text(document: dict) -> str:
    lines = [
        f"@PROJECT.{document['project']}",
        *(f"{name:<{FIELD_NAME_WIDTH}}{document[name]}" for name in TREE_FIELDS if document[name] is not None),
    ]
    return "\n".join(lines)
