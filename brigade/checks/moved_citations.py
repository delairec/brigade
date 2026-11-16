from brigade.checks._read_draft import read_draft
from brigade.checks._report_findings import report_findings
from brigade.runtime import Runtime

NAME = "moved_citations"
SHORT_COMMIT_LENGTH = 8


def _locate(path: str, lines: dict) -> str:
    if lines["start"] == lines["end"]:
        return f"{path}:{lines['start']}"
    return f"{path}:{lines['start']}-{lines['end']}"


def _describe(citation: dict, since: str) -> str:
    if citation["now"] is None:
        return f"{citation['citation']} changed since {since}"
    return f"{citation['citation']} moved since {since} to {_locate(citation['path'], citation['now'])}"


def check(subject: dict, runtime: Runtime) -> dict:
    draft = read_draft(subject)["summary"]
    since = draft["source_commit"][:SHORT_COMMIT_LENGTH]
    findings = [
        _describe(citation, since)
        for citation in draft["citations"]
        if citation["now"] != {"start": citation["start"], "end": citation["end"]}
    ]
    return report_findings(NAME, findings)
