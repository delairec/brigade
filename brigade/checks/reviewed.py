from brigade.checks._report_findings import report_findings
from brigade.runtime import Runtime

NAME = "reviewed"
PR_LIST_COLLECTOR = "pr-list"
PR_PARAMETER = "pr"
NO_REVIEW = 0


def _describe_findings(pull_requests: list, number: int) -> list[str]:
    reviews = next((pull_request["reviews"] for pull_request in pull_requests if pull_request["number"] == number), None)
    if reviews is None:
        return [f"the forge lists no pull request {number}"]
    if reviews == NO_REVIEW:
        return [f"no review was submitted on the pull request {number}"]
    return []


def check(subject: dict, runtime: Runtime) -> dict:
    pull_requests = subject["collected"][PR_LIST_COLLECTOR]["items"]
    return report_findings(NAME, _describe_findings(pull_requests, int(subject["parameters"][PR_PARAMETER])))
