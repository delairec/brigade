from brigade.errors import BrigadeError
from brigade.inbox.inbox_locations import SHOWN_ID_LENGTH
from brigade.inbox.read_inbox import Signal

SHORTEST_PREFIX = 4


def find_signal(signals: tuple[Signal, ...], prefix: str) -> Signal:
    if len(prefix) < SHORTEST_PREFIX:
        raise BrigadeError(f"the id {prefix} is shorter than {SHORTEST_PREFIX} characters")
    matches = [signal for signal in signals if signal.id.startswith(prefix)]
    if not matches:
        raise BrigadeError(f"no signal of the inbox has an id starting with {prefix}")
    if len(matches) > 1:
        candidates = ", ".join(f"{signal.id[:SHOWN_ID_LENGTH]} {signal.fingerprint}" for signal in matches)
        raise BrigadeError(f"{len(matches)} signals of the inbox have an id starting with {prefix}: {candidates}")
    return matches[0]
