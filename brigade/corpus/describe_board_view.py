from collections import Counter

from brigade.corpus.corpus_reader import LITERAL, CorpusReader, display_atoms, read_atoms
from brigade.corpus.rank_naturally import rank_naturally

COLUMNS_SHOWN = 5
NONE_LABEL = "(none)"


def _read_keys(reader: CorpusReader, card: dict, field: str) -> dict[str, str]:
    written = reader.values(reader.row(card["target"])).get(field, [])
    return {read_atoms(atoms): display_atoms(atoms) for atoms in written}


def _describe_column(value: str, label: str, keyed: list[tuple[dict, dict[str, str]]]) -> dict:
    return {"label": label, "value": value, "entities": [card for card, keys in keyed if value in keys]}


def _describe_free_columns(keyed: list[tuple[dict, dict[str, str]]]) -> list[dict]:
    counts = Counter(key for _, keys in keyed for key in keys)
    labels = {key: label for _, keys in keyed for key, label in keys.items()}
    ranked = sorted(counts, key=lambda key: (-counts[key], rank_naturally(key)))
    kept = sorted(ranked[:COLUMNS_SHOWN], key=rank_naturally)
    folded = set(ranked[COLUMNS_SHOWN:])
    columns = [_describe_column(key, labels[key], keyed) for key in kept]
    if not folded:
        return columns
    placed = sorted(
        ((card, key) for card, keys in keyed for key in keys if key in folded),
        key=lambda placing: (rank_naturally(placing[0]["code"]), rank_naturally(placing[1])),
    )
    others = {
        "label": f"Others ({len(folded)})",
        "value": None,
        "entities": [card | {"value": labels[key]} for card, key in placed],
    }
    return [*columns, others]


def describe_board_view(reader: CorpusReader, cards: list[dict], entity_type: str, field: str) -> dict:
    keyed = [(card, _read_keys(reader, card, field)) for card in cards]
    schema = reader.field(entity_type, field)
    if schema is not None and schema.kinds == (LITERAL,):
        written = [key for _, keys in keyed for key in keys]
        values = list(dict.fromkeys([*schema.choices, *written]))
        columns = [_describe_column(value, value, keyed) for value in values]
    else:
        columns = _describe_free_columns(keyed)
    unwritten = [card for card, keys in keyed if not keys]
    if unwritten:
        columns.append({"label": NONE_LABEL, "value": None, "entities": unwritten})
    return {"field": field, "columns": columns}
