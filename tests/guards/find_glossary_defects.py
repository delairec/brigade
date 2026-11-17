import re
from dataclasses import dataclass

BEGIN_MARKER = "<!-- glossary: begin -->"
END_MARKER = "<!-- glossary: end -->"
PAGE = "wiki/Glossary.md"
_PROGRAM = "brigade"
_CELL_SEPARATOR = re.compile(r"(?<!\\)\|")
_HEADER_WORD = "Word"
_COMMAND = "command"
_SCHEMA_KINDS = ("entity", "field")


@dataclass(frozen=True)
class GlossarySources:
    task_milestones: dict[str, str]
    command_paths: list[tuple[str, ...]]
    schema_words: list[str]
    carried_text: str


@dataclass(frozen=True)
class _Row:
    word: str
    kind: str
    milestone: str
    task: str


def _read_rows(page: str) -> list[_Row]:
    table = page.partition(BEGIN_MARKER)[2].partition(END_MARKER)[0]
    cells = [
        [cell.strip() for cell in _CELL_SEPARATOR.split(line.strip())[1:-1]]
        for line in table.splitlines()
        if line.startswith("|")
    ]
    return [
        _Row(word=row[0].strip("`"), kind=row[1], milestone=row[4], task=row[5])
        for row in cells
        if row[0] != _HEADER_WORD and not set(row[0]) <= {"-"}
    ]


def _name_command(path: tuple[str, ...]) -> str:
    return " ".join((_PROGRAM, *path))


def _is_carried(row: _Row, sources: GlossarySources) -> bool:
    if row.kind == _COMMAND:
        return row.word in {_name_command(path) for path in sources.command_paths}
    if row.kind in _SCHEMA_KINDS:
        return row.word in sources.schema_words
    word = re.compile(rf"(?<!\w){re.escape(row.word)}(?!\w)")
    return word.search(sources.carried_text) is not None


def _find_row_defects(row: _Row, sources: GlossarySources) -> list[str]:
    milestone = sources.task_milestones.get(row.task)
    defects = []
    if milestone is None:
        defects.append(f"the row {row.word} of {PAGE} cites @TASK.{row.task}, which the corpus lacks")
    elif milestone != row.milestone:
        defects.append(f"the row {row.word} of {PAGE} names {row.milestone}, where @TASK.{row.task} is of {milestone}")
    if not _is_carried(row, sources):
        defects.append(f"the row {row.word} of {PAGE} names a word neither the code nor the corpus carries")
    return defects


def find_glossary_defects(page: str, sources: GlossarySources) -> list[str]:
    rows = _read_rows(page)
    words = {row.word for row in rows}
    expected = [*(_name_command(path) for path in sources.command_paths), *sources.schema_words]
    return [defect for row in rows for defect in _find_row_defects(row, sources)] + [
        f"{word} has no row in {PAGE}" for word in expected if word not in words
    ]
