from string import Template

from brigade.tasks.describe_pull_request_body import BODY_TEMPLATE
from brigade.verify.judge_findings import judge_findings

NAME = "body"


def _list_placeholders() -> list[str]:
    template = Template(BODY_TEMPLATE.read_text(encoding="utf-8"))
    return [match["named"] or match["braced"] for match in template.pattern.finditer(template.template)]


def check_body(body: str, title: str) -> dict:
    opening = next(iter(body.splitlines()), "")
    findings = []
    if opening != title:
        findings.append(f"the body opens on {opening}, not on the TITLE of the task, {title}")
    findings.extend(
        f"the body keeps the placeholder ${name}"
        for name in _list_placeholders()
        if f"${name}" in body or f"${{{name}}}" in body
    )
    return judge_findings(NAME, findings)
