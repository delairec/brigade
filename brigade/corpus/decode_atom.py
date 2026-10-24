import re

QUOTE = '"'
AWAWA_ESCAPE = re.compile(r'\\([\\"])')


def decode_atom(atom: str) -> str:
    if not atom.startswith(QUOTE):
        return atom
    return AWAWA_ESCAPE.sub(r"\1", atom[1:-1])
