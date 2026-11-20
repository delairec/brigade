import re

PART_SEPARATOR = "_"
WORD_SEPARATOR = " "
CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
WRITTEN_AS_A_CODE = re.compile(r"[A-Z0-9]+")


def _spell(word: str, rank: int) -> str:
    if rank == 0 or WRITTEN_AS_A_CODE.fullmatch(word):
        return word
    return word.lower()


def read_name_as_sentence(name: str) -> str:
    words = [word for part in name.split(PART_SEPARATOR) for word in CASE_BOUNDARY.split(part) if word]
    return WORD_SEPARATOR.join(_spell(word, rank) for rank, word in enumerate(words))
