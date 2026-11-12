from typing import TextIO


def ask_on_terminal(answering: TextIO | None, prompting: TextIO, question: str) -> str | None:
    if answering is None or not answering.isatty():
        return None
    prompting.write(question)
    prompting.flush()
    return answering.readline().strip()
