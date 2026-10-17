from dataclasses import dataclass

from brigade.errors import BrigadeError

SPACE = " "
HYPHEN = "-"


@dataclass(frozen=True)
class PullRequestTitleParts:
    type: str
    component: str | None
    subject: str | None
    task: str


def _describe_scope(component: str | None) -> str:
    if component is None:
        return ""
    return f"({component.replace(SPACE, HYPHEN)})"


def compose_pull_request_title(parts: PullRequestTitleParts) -> str:
    if parts.subject is None or not parts.subject.strip():
        raise BrigadeError("brigade task pr needs --subject, the subject of the pull request in the imperative")
    return f"{parts.type}{_describe_scope(parts.component)}: {parts.subject} (@TASK.{parts.task})"
