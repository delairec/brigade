import re

from brigade.waves.delivery import Delivery

BRIGADE_SUBJECTS = (
    re.compile(r"^docs\(corpus\): mark @TASK\.\S+ implemented, delivered by #\d+$"),
    re.compile(r"^docs\(waves\): add the report of \S+$"),
)
NAME_SEPARATOR = ", "


def _open_on_the_delivered(delivery: Delivery) -> str:
    milestone = delivery.milestone
    if delivery.wave is None:
        waves = NAME_SEPARATOR.join(f"{merged.wave} (#{merged.pr})" for merged in delivery.merged_waves)
        return f"Delivers the milestone {milestone.name} ({milestone.title}) into {delivery.base}: its waves {waves}."
    of = "of no milestone" if milestone is None else f"of the milestone {milestone.name} ({milestone.title})"
    tasks = NAME_SEPARATOR.join(f"@TASK.{task.name}" for task in delivery.tasks)
    return f"Delivers the wave {delivery.wave} {of} into {delivery.base}: {tasks}."


def _is_described_elsewhere(subject: str, delivery: Delivery) -> bool:
    return any(subject in task.pr_commits for task in delivery.tasks) or any(
        pattern.match(subject) for pattern in BRIGADE_SUBJECTS
    )


def compose_delivery_body(delivery: Delivery) -> str:
    if delivery.report is not None:
        return delivery.report
    tasks = [f"- @TASK.{task.name} — {task.title} (#{task.pr})" for task in delivery.tasks]
    commits = [f"- {subject}" for subject in delivery.commits if not _is_described_elsewhere(subject, delivery)]
    attribution = ["", *delivery.attribution] if delivery.attribution else []
    return "\n".join([_open_on_the_delivered(delivery), "", *tasks, *commits, *attribution])
