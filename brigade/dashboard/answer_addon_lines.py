import json
from collections.abc import Callable
from typing import TextIO


def _answer_line(line: str, answer: Callable[[dict], dict]) -> dict:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as error:
        return {"error": f"the request is not JSON: {error}"}
    return answer(message)


def answer_addon_lines(reader: TextIO, writer: TextIO, answer: Callable[[dict], dict]) -> int:
    answered = 0
    for line in reader:
        writer.write(f"{json.dumps(_answer_line(line, answer))}\n")
        writer.flush()
        answered += 1
    return answered
