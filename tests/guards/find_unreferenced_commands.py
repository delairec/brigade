import re

_CODE_SPAN = re.compile(r"`([^`]+)`")
_WORD_SEPARATOR = re.compile(r"\\\||[\s|\[\]]+")
_PROGRAM = "brigade"


def _read_spans(line: str) -> list[list[str]]:
    return [_WORD_SEPARATOR.split(span) for span in _CODE_SPAN.findall(line)]


def _is_named(path: tuple[str, ...], lines: list[list[list[str]]]) -> bool:
    command, *subcommand = path
    return any(
        [_PROGRAM, command] in [words[:2] for words in spans]
        and set(subcommand) <= {word for words in spans for word in words}
        for spans in lines
    )


def find_unreferenced_commands(page: str, command_paths: list[tuple[str, ...]]) -> list[str]:
    lines = [_read_spans(line) for line in page.splitlines()]
    return [
        f"{_PROGRAM} {' '.join(path)} has no line in wiki/Command-reference.md"
        for path in command_paths
        if not _is_named(path, lines)
    ]
