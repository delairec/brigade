import re

_CODE_SPAN = re.compile(r"`([^`]+)`")
_WORD_SEPARATOR = re.compile(r"\\\||[\s|\[\]]+")
_PROGRAM = "brigade"


def _read_spans(line: str) -> list[list[str]]:
    return [_WORD_SEPARATOR.split(span) for span in _CODE_SPAN.findall(line)]


def _is_named_on(path: tuple[str, ...], spans: list[list[str]]) -> bool:
    command, *subcommand = path
    spans_of_command = [words for words in spans if words[:2] == [_PROGRAM, command]]
    spans_of_no_command = [words for words in spans if words[:1] != [_PROGRAM]]
    return bool(spans_of_command) and set(subcommand) <= {
        word for words in spans_of_command + spans_of_no_command for word in words
    }


def _is_named(path: tuple[str, ...], lines: list[list[list[str]]]) -> bool:
    return any(_is_named_on(path, spans) for spans in lines)


def find_unreferenced_commands(page: str, command_paths: list[tuple[str, ...]]) -> list[str]:
    lines = [_read_spans(line) for line in page.splitlines()]
    return [
        f"{_PROGRAM} {' '.join(path)} has no line in wiki/Command-reference.md"
        for path in command_paths
        if not _is_named(path, lines)
    ]
