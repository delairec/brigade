def read_run_question(message: str | None) -> str:
    if message is None:
        return ""
    return " ".join(line.strip() for line in message.splitlines()[:-1] if line.strip())
