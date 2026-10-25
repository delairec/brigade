import hashlib

FINGERPRINT_LENGTH = 12
NO_PROJECT_NAME = ""


def fingerprint_note(project: str | None, text: str) -> str:
    content = f"{project or NO_PROJECT_NAME}\n{text}"
    return f"note:{hashlib.sha256(content.encode()).hexdigest()[:FINGERPRINT_LENGTH]}"
