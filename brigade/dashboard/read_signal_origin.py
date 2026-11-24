from dataclasses import dataclass

SEPARATOR = ":"
NO_PROJECT = "-"
NO_WAVE = None
SCAN_KIND = "scan"
STALL_KIND = "stall"
CHECK_RUN_KIND = "check_run"
GROUPS = {STALL_KIND: "Stalls", CHECK_RUN_KIND: "Check runs", "note": "Notes", "review_thread": "Review threads"}


@dataclass(frozen=True)
class SignalOrigin:
    group: str
    subject: str
    wave: str | None
    last_action: str | None = None


def _name_check_run(fingerprint: str) -> str:
    _, _, subject, written = fingerprint.split(SEPARATOR, 3)
    check = written.rpartition(SEPARATOR)[0]
    return f"PR {subject} · {check}" if subject.isdigit() else f"{subject} · {check}"


def read_signal_origin(signal: dict) -> SignalOrigin:
    kind = signal["kind"]
    fingerprint = signal["fingerprint"]
    if kind == SCAN_KIND:
        scan, _, subject = fingerprint.split(SEPARATOR, 2)
        return SignalOrigin(group=f"Scan {scan}", subject=subject, wave=NO_WAVE)
    if kind == STALL_KIND:
        _, _, wave, task = fingerprint.split(SEPARATOR, 3)
        return SignalOrigin(group=GROUPS[kind], subject=task, wave=wave, last_action=signal["last_action"])
    if kind == CHECK_RUN_KIND:
        return SignalOrigin(group=GROUPS[kind], subject=_name_check_run(fingerprint), wave=NO_WAVE)
    return SignalOrigin(group=GROUPS.get(kind, kind), subject=signal["project"] or NO_PROJECT, wave=NO_WAVE)
