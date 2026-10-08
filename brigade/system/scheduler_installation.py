from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulerInstallation:
    scheduler: str
    unit_files: tuple[str, ...]
    cron_line: str | None
    keep_running: str | None

    @classmethod
    def from_document(cls, document: dict) -> "SchedulerInstallation":
        return cls(
            scheduler=document["scheduler"],
            unit_files=tuple(document["unit_files"]),
            cron_line=document["cron_line"],
            keep_running=document["keep_running"],
        )
