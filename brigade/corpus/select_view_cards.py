from brigade.corpus.corpus_reader import CorpusReader, CorpusRow, is_reference_atom, read_atoms
from brigade.corpus.describe_entity_card import describe_entity_card
from brigade.corpus.view_request import ViewRequest
from brigade.errors import BrigadeError

VALUE_SEPARATOR = "="
FIELD_SEPARATOR = "."


def _read_filters(filters: tuple[str, ...]) -> dict[str, set[str]]:
    wanted: dict[str, set[str]] = {}
    for written in filters:
        field, separator, value = written.partition(VALUE_SEPARATOR)
        if not separator:
            raise BrigadeError(f"--filter takes <field>=<value>, given {written}")
        wanted.setdefault(field, set()).add(value)
    return wanted


def _read_values(reader: CorpusReader, row: CorpusRow, path: str) -> set[str]:
    field, _, referred_field = path.partition(FIELD_SEPARATOR)
    written = reader.values(row).get(field, [])
    if not referred_field:
        return {read_atoms(atoms) for atoms in written}
    referred = [reader.row(atom) for atoms in written for atom in atoms if is_reference_atom(atom)]
    return {value for other in referred if other is not None for value in _read_values(reader, other, referred_field)}


def _holds(reader: CorpusReader, row: CorpusRow, wanted: dict[str, set[str]]) -> bool:
    return all(_read_values(reader, row, path) & values for path, values in wanted.items())


def describe_searched_texts(card: dict) -> list[str]:
    facts = [value["text"] for fact in card["facts"] for value in fact["values"]]
    return [card["label"], card["code"], *facts, card["status"] or "", card["file"]]


def carries_search(texts: list[str], search: str | None) -> bool:
    return search is None or any(search.casefold() in text.casefold() for text in texts)


def select_view_cards(reader: CorpusReader, rows: list[CorpusRow], request: ViewRequest) -> list[dict]:
    wanted = _read_filters(request.filters)
    reader.prefetch(rows)
    kept = [row for row in rows if row.type != request.entity_type or _holds(reader, row, wanted)]
    cards = [describe_entity_card(reader, row) for row in kept]
    return [card for card in cards if carries_search(describe_searched_texts(card), request.search)]
