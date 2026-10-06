def describe_skipped_lines(document: dict) -> list[str]:
    return [f"skipped {line['file']}:{line['line']}: {line['reason']}" for line in document["skipped"]]
