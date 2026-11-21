from dataclasses import dataclass
from importlib.resources import files
from string import Template

BODY_TEMPLATE = files("brigade.tasks") / "data" / "pull-request-body.md.tpl"
OK = "ok"
FAILED = "fail"
MS_PER_S = 1000


@dataclass(frozen=True)
class Correction:
    pr: int
    task: str | None


@dataclass(frozen=True)
class PullRequestBodyParts:
    corrections: tuple[Correction, ...]
    title: str
    specs: tuple[str, ...]
    check: dict
    attribution: tuple[str, ...]
    captures: str


def _describe_check(check: dict) -> str:
    result = OK if check["passed"] else FAILED
    return f"- {result} `{check['command']}` {check['duration_ms'] / MS_PER_S:.1f} s"


def _describe_correction(correction: Correction) -> str:
    task = "" if correction.task is None else f" (@TASK.{correction.task})"
    return f"Corrects #{correction.pr}{task}\n"


def _describe_corrections(corrections: tuple[Correction, ...]) -> str:
    if not corrections:
        return ""
    return "".join(map(_describe_correction, corrections)) + "\n"


def _describe_captures(captures: str) -> str:
    if not captures:
        return captures
    return f"{captures}\n"


def describe_pull_request_body(parts: PullRequestBodyParts) -> str:
    return Template(BODY_TEMPLATE.read_text(encoding="utf-8")).substitute(
        corrections=_describe_corrections(parts.corrections),
        title=parts.title,
        specs="\n".join(f"- {spec}" for spec in parts.specs),
        head=parts.check["head"],
        checks="\n".join(_describe_check(check) for check in parts.check["checks"]),
        captures=_describe_captures(parts.captures),
        attribution="\n".join(parts.attribution),
    )
