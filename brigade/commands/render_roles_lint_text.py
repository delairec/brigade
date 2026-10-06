def _render_finding(finding: dict) -> str:
    if finding["key"] is None:
        return f"{finding['file']}: {finding['problem']}"
    return f"{finding['file']}: {finding['key']} {finding['problem']}"


def _summarise(document: dict) -> str:
    count = len(document["findings"])
    noun = "finding" if count == 1 else "findings"
    return f"roles lint: {len(document['files'])} files, {count} {noun}"


def render_roles_lint_text(document: dict) -> str:
    if not document["findings"]:
        return _summarise(document)
    return "\n".join([*(_render_finding(finding) for finding in document["findings"]), "", _summarise(document)])
