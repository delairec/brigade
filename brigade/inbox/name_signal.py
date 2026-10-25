import hashlib


def name_signal(fingerprint: str) -> str:
    return hashlib.sha256(fingerprint.encode()).hexdigest()
