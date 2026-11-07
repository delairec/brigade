from dataclasses import dataclass


@dataclass(frozen=True)
class MilestoneReportOrder:
    project: str
    milestone: str
    branch: str
    waves: tuple[str, ...]
    tasks: tuple[str, ...]
