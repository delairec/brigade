from dataclasses import dataclass

from brigade.errors import BrigadeError

FENCE = "---"
SEPARATOR = ":"
FIRST_KEY_LINE_NUMBER = 2


class RoleFileUnreadable(BrigadeError):
    pass


@dataclass(frozen=True)
class RoleFile:
    front_matter: dict
    body: str


def _read_entry(line: str, line_number: int) -> tuple[str, str]:
    key, separator, value = line.partition(SEPARATOR)
    if not separator or not key.strip():
        raise RoleFileUnreadable(f"line {line_number} is not key: value")
    return key.strip(), value.strip()


def _read_front_matter(lines: list[str]) -> dict:
    front_matter = {}
    for line_number, line in enumerate(lines, start=FIRST_KEY_LINE_NUMBER):
        key, value = _read_entry(line, line_number)
        if key in front_matter:
            raise RoleFileUnreadable(f"declares {key} twice")
        front_matter[key] = value
    return front_matter


def parse_role_file(text: str) -> RoleFile:
    lines = text.splitlines(keepends=True)
    stripped = [line.rstrip("\r\n") for line in lines]
    if not stripped or stripped[0] != FENCE or FENCE not in stripped[1:]:
        raise RoleFileUnreadable("has no front matter between two --- lines")
    closing = stripped.index(FENCE, 1)
    return RoleFile(front_matter=_read_front_matter(stripped[1:closing]), body="".join(lines[closing + 1 :]))
