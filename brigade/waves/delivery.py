from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveredTask:
    name: str
    title: str
    type: str
    component: str | None
    pr: int
    pr_title: str
    pr_commits: tuple[str, ...]


@dataclass(frozen=True)
class DeliveredMilestone:
    name: str
    title: str


@dataclass(frozen=True)
class DeliveredWave:
    wave: str
    pr: int


@dataclass(frozen=True)
class Delivery:
    wave: str | None
    milestone: DeliveredMilestone | None
    base: str
    merged_waves: tuple[DeliveredWave, ...]
    tasks: tuple[DeliveredTask, ...]
    commits: tuple[str, ...]
    attribution: tuple[str, ...]
    report: str | None
