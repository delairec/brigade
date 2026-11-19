import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path

from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.rank_naturally import rank_naturally
from brigade.corpus.read_name_as_sentence import read_name_as_sentence
from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

UNREADABLE_NAME = "?"
STATUS_FIELD = "STATUS"
LITERAL = "literal"
REFERENCE_MARK = "@"
NAME_SEPARATOR = "."
ATOM_SEPARATOR = " "
QUOTE = '"'
LINT_IN_ERROR = 1
LINTED = (0, LINT_IN_ERROR)
PARALLEL_SHOWS = 8


@dataclass(frozen=True)
class FieldSchema:
    name: str
    required: bool
    repeatable: bool
    kinds: tuple[str, ...]
    choices: tuple[str, ...]
    referred: tuple[str, ...]


@dataclass(frozen=True)
class CorpusRow:
    type: str
    name: str
    target: str
    status: str | None
    file: str
    line: int
    path: str


def is_reference_atom(atom: str) -> bool:
    return atom.startswith(REFERENCE_MARK)


def display_atoms(atoms: tuple[str, ...]) -> str:
    return ATOM_SEPARATOR.join(
        read_name_as_sentence(atom.partition(NAME_SEPARATOR)[2]) if is_reference_atom(atom) else decode_atom(atom)
        for atom in atoms
    )


def read_atoms(atoms: tuple[str, ...]) -> str:
    return ATOM_SEPARATOR.join(map(decode_atom, atoms))


def _read_field_schema(field: dict) -> FieldSchema:
    slots = [slot for alternatives in field["slots"] for slot in alternatives]
    return FieldSchema(
        name=field["name"],
        required=field["required"],
        repeatable=field["repeatable"],
        kinds=tuple(dict.fromkeys(slot["kind"] for slot in slots)),
        choices=tuple(slot["value"] for slot in slots if slot["kind"] == LITERAL),
        referred=tuple(slot["type"] for slot in slots if "type" in slot),
    )


class CorpusReader:
    def __init__(self, run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, ide_link: str):
        self.run_process = run_process
        self.root = root
        self.ide_link = ide_link
        self.read_context = cache(self._read_context)
        self.show = cache(self._show)
        self.fields = cache(self._read_fields)
        self.lint = cache(self._lint)

    def _read_document(self, arguments: tuple[str, ...], acceptable_exit_codes: tuple[int, ...] = SUCCESS) -> dict:
        record = run_awawa(self.run_process, self.root, (*arguments, "--json", str(self.root)), acceptable_exit_codes)
        return json.loads(record.stdout)

    @cached_property
    def status(self) -> dict:
        return self._read_document(("status",))

    @cached_property
    def rows(self) -> list[CorpusRow]:
        listed = [entity for entity in self.status["entities"] if entity["name"] != UNREADABLE_NAME]
        return [
            CorpusRow(
                type=entity["type"],
                name=entity["name"],
                target=entity["target"],
                status=entity["status"],
                file=self.relative_file(entity["file"]),
                line=entity["line"],
                path=entity["file"],
            )
            for entity in listed
        ]

    def relative_file(self, file: str) -> str:
        return str(Path(file).relative_to(self.root))

    @cached_property
    def _rows_by_target(self) -> dict[str, CorpusRow]:
        return {row.target: row for row in self.rows}

    def row(self, target: str) -> CorpusRow | None:
        return self._rows_by_target.get(target)

    def rows_of(self, entity_type: str) -> list[CorpusRow]:
        return sorted((row for row in self.rows if row.type == entity_type), key=lambda row: rank_naturally(row.name))

    def link(self, row: CorpusRow) -> str | None:
        if not self.ide_link:
            return None
        return self.ide_link.replace("{path}", row.path).replace("{line}", str(row.line))

    def _read_context(self, target: str) -> dict:
        return self._read_document(("context", target, "--depth", "0", "--with-schema"))

    def _read_fields(self, entity_type: str) -> tuple[FieldSchema, ...]:
        first = next(row for row in self.rows if row.type == entity_type)
        resolved = self.read_context(first.target)["resolved"].get(entity_type, {"fields": []})
        return tuple(map(_read_field_schema, resolved["fields"]))

    def field(self, entity_type: str, name: str) -> FieldSchema | None:
        return next((field for field in self.fields(entity_type) if field.name == name), None)

    def lifecycle(self, entity_type: str) -> tuple[str, ...]:
        status = self.field(entity_type, STATUS_FIELD)
        return () if status is None else status.choices

    def _show(self, target: str) -> dict:
        return self._read_document(("show", target))

    def values(self, row: CorpusRow) -> dict[str, list[tuple[str, ...]]]:
        values: dict[str, list[tuple[str, ...]]] = {}
        for field in self.show(row.target)["fields"]:
            values.setdefault(field["name"], []).append(tuple(field["atoms"]))
        return values

    def prefetch(self, rows: list[CorpusRow]) -> None:
        with ThreadPoolExecutor(PARALLEL_SHOWS) as executor:
            list(executor.map(self.show, [row.target for row in rows]))

    def _lint(self) -> dict:
        return self._read_document(("lint",), LINTED)
