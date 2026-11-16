from brigade.checks._read_draft import read_draft
from brigade.checks._report_findings import report_findings
from brigade.runtime import Runtime

NAME = "tasks_outside_after"


def check(subject: dict, runtime: Runtime) -> dict:
    draft = read_draft(subject)
    summary = draft["summary"]
    findings = []
    for task in draft["items"]:
        shared_files = sorted(set(task["files"]) & set(summary["files"]))
        if shared_files and task["task"] not in summary["after"]:
            findings.append(
                f"@TASK.{task['task']} ({task['status']}) touches {', '.join(shared_files)},"
                f" outside the AFTER of @TASK.{summary['task']}"
            )
    return report_findings(NAME, findings)
