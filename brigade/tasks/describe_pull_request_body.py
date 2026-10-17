from dataclasses import dataclass
from importlib.resources import files
from string import Template

BODY_TEMPLATE = files("brigade.tasks") / "data" / "pull-request-body.md.tpl"
PASSED = "pass"
FAILED = "fail"
MS_PER_S = 1000


@dataclass(frozen=True)
class PullRequestBodyParts:
    title: str
    specs: tuple[str, ...]
    check: dict
    attribution: tuple[str, ...]


def _describe_check(check: dict) -> str:
    verdict = PASSED if check["passed"] else FAILED
    return f"- {verdict} `{check['command']}` {check['duration_ms'] / MS_PER_S:.1f} s"


def describe_pull_request_body(parts: PullRequestBodyParts) -> str:
    return Template(BODY_TEMPLATE.read_text(encoding="utf-8")).substitute(
        title=parts.title,
        specs="\n".join(f"- {spec}" for spec in parts.specs),
        head=parts.check["head"],
        checks="\n".join(_describe_check(check) for check in parts.check["checks"]),
        attribution="\n".join(parts.attribution),
    )
