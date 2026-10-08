from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulerState:
    installed: bool
    unit_files: tuple[str, ...]
    cron_line: str | None
    next_activation: str | None

    @classmethod
    def from_document(cls, document: dict) -> "SchedulerState":
        return cls(
            installed=document["installed"],
            unit_files=tuple(document["unit_files"]),
            cron_line=document["cron_line"],
            next_activation=document["next_activation"],
        )
