import re

PIECE = re.compile(r"\d+|\D+")


def rank_naturally(name: str) -> tuple:
    return tuple((0, int(piece), "") if piece.isdigit() else (1, 0, piece.casefold()) for piece in PIECE.findall(name))
