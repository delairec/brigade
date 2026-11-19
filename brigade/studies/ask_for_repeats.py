REPEATS_FIELD = "REPEATS"
REPEATS_QUESTION = (
    " A new PATTERN that repeats a PATTERN the registry holds all the same names it in REPEATS, @PATTERN.<its name>."
)


def ask_for_repeats(question: str, declared_fields: tuple[str, ...]) -> str:
    if REPEATS_FIELD not in declared_fields:
        return question
    return question + REPEATS_QUESTION
