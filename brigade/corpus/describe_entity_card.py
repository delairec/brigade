from brigade.corpus.corpus_reader import (
    STATUS_FIELD,
    CorpusReader,
    CorpusRow,
    FieldSchema,
    display_atoms,
    is_reference_atom,
)
from brigade.corpus.read_name_as_sentence import read_name_as_sentence

FACTS_SHOWN = 4
STRING = ("string",)
FACT_KINDS = {"literal", "int", "uint", "number", "identifier", "ref", "reference", "shape"}


def _is_label(field: FieldSchema) -> bool:
    return field.required and not field.repeatable and field.kinds == STRING


def _is_fact(field: FieldSchema) -> bool:
    return field.name != STATUS_FIELD and FACT_KINDS.issuperset(field.kinds)


def _describe_label(reader: CorpusReader, row: CorpusRow) -> str:
    field = next(filter(_is_label, reader.fields(row.type)), None)
    written = reader.values(row).get(field.name) if field else None
    return display_atoms(written[0]) if written else read_name_as_sentence(row.name)


def _describe_fact_value(reader: CorpusReader, atoms: tuple[str, ...]) -> dict:
    target = atoms[0] if is_reference_atom(atoms[0]) else None
    referred = reader.row(target) if target else None
    return {"text": display_atoms(atoms), "target": target, "status": referred.status if referred else None}


def _describe_facts(reader: CorpusReader, row: CorpusRow) -> list[dict]:
    values = reader.values(row)
    facts = [
        {"field": field.name, "values": [_describe_fact_value(reader, atoms) for atoms in values[field.name]]}
        for field in reader.fields(row.type)
        if _is_fact(field) and field.name in values
    ]
    return facts[:FACTS_SHOWN]


def locate_in_lifecycle(reader: CorpusReader, entity_type: str, status: str | None) -> int | None:
    lifecycle = reader.lifecycle(entity_type)
    return lifecycle.index(status) if status in lifecycle else None


def _waits(reader: CorpusReader, row: CorpusRow, position: int | None) -> bool:
    if position is None:
        return False
    lifecycle = reader.lifecycle(row.type)
    atoms = [atom for written in reader.values(row).values() for atoms in written for atom in atoms]
    referred = [reader.row(atom) for atom in atoms if atom.startswith(f"@{row.type}.")]
    return any(
        other.status not in lifecycle or lifecycle.index(other.status) <= position
        for other in referred
        if other is not None
    )


def describe_entity_card(reader: CorpusReader, row: CorpusRow) -> dict:
    position = locate_in_lifecycle(reader, row.type, row.status)
    return {
        "type": row.type,
        "target": row.target,
        "code": row.name,
        "label": _describe_label(reader, row),
        "facts": _describe_facts(reader, row),
        "status": row.status,
        "position": position,
        "waiting": _waits(reader, row, position),
        "file": row.file,
        "line": row.line,
        "ide_link": reader.link(row),
    }
