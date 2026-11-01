from collections import Counter

from brigade.mining.read_sessions import SessionRead
from brigade.system.transcripts_answer import TranscriptMessage

CORRECTION = "correction"
REFUSAL = "refusal"
REPEATED_COMMAND = "repeated_command"
OVERSIZED_RE_READ = "oversized_re_read"
USER_ROLE = "user"
RUNS_OF_A_REPEATED_COMMAND = 3
FIRST_POSITION = 1

Positioned = list[tuple[int, TranscriptMessage]]


def _detect_corrections(messages: Positioned) -> list[tuple[str, int]]:
    said = [position for position, message in messages if message.role == USER_ROLE and not message.results]
    return [(CORRECTION, position) for position in said[1:]]


def _detect_refusals(messages: Positioned) -> list[tuple[str, int]]:
    return [(REFUSAL, position) for position, message in messages if any(marks.refused for marks in message.results)]


def _detect_repeated_commands(messages: Positioned) -> list[tuple[str, int]]:
    runs = Counter()
    found = []
    for position, message in messages:
        for call in message.calls:
            runs[call] += 1
            if runs[call] == RUNS_OF_A_REPEATED_COMMAND:
                found.append((REPEATED_COMMAND, position))
    return found


def _detect_oversized_re_reads(messages: Positioned) -> list[tuple[str, int]]:
    places = set()
    found = []
    for position, message in messages:
        if any(place in call for call in message.calls for place in places):
            found.append((OVERSIZED_RE_READ, position))
        places.update(marks.truncated for marks in message.results if marks.truncated is not None)
    return found


DETECTORS = (_detect_corrections, _detect_refusals, _detect_repeated_commands, _detect_oversized_re_reads)


def detect_findings(session: SessionRead) -> list[dict]:
    finished = session.finished
    messages = list(enumerate(session.messages, start=FIRST_POSITION))
    detections = sorted(
        (detection for detect in DETECTORS for detection in detect(messages)), key=lambda found: (found[1], found[0])
    )
    return [
        {
            "detector": detector,
            "client": finished.client,
            "session": finished.session,
            "run": finished.run,
            "position": position,
            "fingerprint": f"{detector}:{finished.client}:{finished.session}:{position}",
            "cost_usd": finished.cost_usd,
            "usage": None if finished.usage is None else finished.usage.to_document(),
        }
        for detector, position in detections
    ]
