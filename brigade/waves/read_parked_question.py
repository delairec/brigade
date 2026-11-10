import re

BLOCKED_RUN_REASON = "run {run} blocked: {question}"
BLOCKED_RUN_SHAPE = re.compile(r"run \S+ blocked: (?P<question>.*)", re.DOTALL)
NO_QUESTION = None


def read_parked_question(reason: str) -> str | None:
    match = BLOCKED_RUN_SHAPE.fullmatch(reason)
    return NO_QUESTION if match is None else match["question"]
