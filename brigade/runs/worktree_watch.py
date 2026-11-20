from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WorktreeWatch:
    sampled: bool
    changed_at: datetime | None


NOT_SAMPLED = WorktreeWatch(sampled=False, changed_at=None)
