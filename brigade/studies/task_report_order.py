from dataclasses import dataclass


@dataclass(frozen=True)
class TaskReportOrder:
    project: str
    task: str
    wave: str
    branch: str
