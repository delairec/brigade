import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from brigade.inbox.read_inbox import Signal

CITED_RULE = re.compile(r"@RULE\.\w+")
PATH_KEY = "path"
CHECK_NAME_KEY = "name"
CHECK_RUN_KIND = "check_run"
SINGLE_SIGNAL = "signal"
SMALLEST_FAMILY = 2


@dataclass(frozen=True)
class SignalFamily:
    by: str
    key: str
    signals: tuple[Signal, ...]


def _read_cited_rules(signal: Signal) -> list[str]:
    return sorted(
        {rule for text in signal.evidence.values() if isinstance(text, str) for rule in CITED_RULE.findall(text)}
    )


def _read_file(signal: Signal) -> list[str]:
    path = signal.evidence.get(PATH_KEY)
    return [path] if isinstance(path, str) else []


def _read_check_name(signal: Signal) -> list[str]:
    name = signal.evidence.get(CHECK_NAME_KEY)
    return [name] if signal.kind == CHECK_RUN_KIND and isinstance(name, str) else []


FAMILY_KEYS: tuple[tuple[str, Callable[[Signal], list[str]]], ...] = (
    ("rule", _read_cited_rules),
    ("file", _read_file),
    ("check", _read_check_name),
)


def group_signals(signals: Sequence[Signal]) -> tuple[SignalFamily, ...]:
    families = []
    grouped = set()
    for by, read_keys in FAMILY_KEYS:
        members: dict[str, list[Signal]] = {}
        for signal in signals:
            for key in read_keys(signal):
                members.setdefault(key, []).append(signal)
        for key in sorted(members):
            if len(members[key]) >= SMALLEST_FAMILY:
                families.append(SignalFamily(by=by, key=key, signals=tuple(members[key])))
                grouped.update(signal.fingerprint for signal in members[key])
    alone = [signal for signal in signals if signal.fingerprint not in grouped]
    return (
        *families,
        *(SignalFamily(by=SINGLE_SIGNAL, key=signal.fingerprint, signals=(signal,)) for signal in alone),
    )
