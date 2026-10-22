from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TaskReviewAnswered:
    name: ClassVar[str] = "task.review_answered"
    project: str
    wave: str
    task: str
    pr: int
    head: str
    answers: tuple[dict, ...]
    login: str | None

    @classmethod
    def from_document(cls, document: dict) -> "TaskReviewAnswered":
        return cls(
            project=document["project"],
            wave=document["wave"],
            task=document["task"],
            pr=document["pr"],
            head=document["head"],
            answers=tuple(document["answers"]),
            login=document["login"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "wave": self.wave,
            "task": self.task,
            "pr": self.pr,
            "head": self.head,
            "answers": list(self.answers),
            "login": self.login,
        }
