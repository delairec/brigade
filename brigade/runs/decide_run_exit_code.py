RUN_EXIT_CODES = {
    "done": 0,
    "failed": 1,
    "undeclared": 3,
    "blocked": 10,
    "wall_limit": 11,
    "turn_limit": 12,
    "handed_over": 20,
    "stopped": 21,
}


def decide_run_exit_code(outcome: str | None) -> int:
    return RUN_EXIT_CODES.get(outcome, RUN_EXIT_CODES["failed"])
