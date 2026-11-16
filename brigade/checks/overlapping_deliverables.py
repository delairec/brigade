from brigade.checks._read_draft import read_draft
from brigade.checks._report_findings import report_findings
from brigade.runtime import Runtime

NAME = "overlapping_deliverables"


def check(subject: dict, runtime: Runtime) -> dict:
    draft = read_draft(subject)
    summary = draft["summary"]
    findings = []
    for task in draft["items"]:
        shared = [
            *sorted(set(task["files"]) & set(summary["files"])),
            *sorted(set(task["entities"]) & set(summary["entities"])),
        ]
        if shared:
            findings.append(
                f"@TASK.{task['task']} ({task['status']}) cites {', '.join(shared)} as @TASK.{summary['task']} does"
            )
    return report_findings(NAME, findings)
