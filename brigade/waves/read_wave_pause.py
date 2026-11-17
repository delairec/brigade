from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.format_instant import format_instant
from brigade.ledger.wave_blocked import WaveBlocked
from brigade.ledger.wave_parked import WaveParked
from brigade.ledger.wave_resumed import WaveResumed


@dataclass(frozen=True)
class WavePause:
    reason: str
    resume_at: datetime | None

    def to_document(self) -> dict:
        return {"reason": self.reason, "resume_at": None if self.resume_at is None else format_instant(self.resume_at)}


def read_wave_pause(events: tuple, wave: str) -> WavePause | None:
    pause = None
    for event in (event for event in events if getattr(event, "wave", None) == wave):
        if isinstance(event, WaveParked):
            pause = WavePause(reason=event.reason, resume_at=None)
        elif isinstance(event, WaveBlocked):
            pause = WavePause(reason=event.reason, resume_at=datetime.fromisoformat(event.resume_at))
        elif isinstance(event, WaveResumed):
            pause = None
    return pause
