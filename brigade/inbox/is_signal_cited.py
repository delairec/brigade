EVIDENCE_SEPARATOR = " "


def is_signal_cited(evidence: str, fingerprint: str) -> bool:
    return evidence == fingerprint or evidence.startswith(fingerprint + EVIDENCE_SEPARATOR)
