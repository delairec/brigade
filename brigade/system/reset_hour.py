from dataclasses import dataclass


@dataclass(frozen=True)
class ResetHour:
    hour: str
    timezone: str | None

    @classmethod
    def from_document(cls, document: dict) -> "ResetHour":
        return cls(hour=document["hour"], timezone=document["timezone"])

    def to_document(self) -> dict:
        return {"hour": self.hour, "timezone": self.timezone}
