from brigade.corpus.corpus_reader import CorpusReader

SCHEMA_TYPES = ("SCHEMA", "FIELDSET", "SHAPE")


def _count_statuses(reader: CorpusReader, entity_type: str) -> int:
    return len({row.status for row in reader.rows_of(entity_type) if row.status is not None})


def _is_grouped(reader: CorpusReader, entity_type: str) -> bool:
    rows = reader.rows_of(entity_type)
    return 2 * sum(row.status is not None for row in rows) >= len(rows)


def _describe_groups(reader: CorpusReader, entity_type: str, cards: list[dict]) -> list[dict]:
    lifecycle = reader.lifecycle(entity_type)
    statuses = list(dict.fromkeys([*lifecycle, *(card["status"] for card in cards if card["status"] is not None)]))
    groups = [
        {
            "status": status,
            "collapsed": lifecycle[-1:] == (status,),
            "entities": [card for card in cards if card["status"] == status],
        }
        for status in statuses
    ]
    unset = {"status": None, "collapsed": False, "entities": [card for card in cards if card["status"] is None]}
    return [group for group in [*groups, unset] if group["entities"]]


def _describe_type(reader: CorpusReader, entity_type: str, cards: list[dict]) -> dict:
    own = [card for card in cards if card["type"] == entity_type]
    if _is_grouped(reader, entity_type):
        return {"type": entity_type, "groups": _describe_groups(reader, entity_type, own)}
    return {"type": entity_type, "entities": own}


def describe_tree_view(reader: CorpusReader, cards: list[dict]) -> dict:
    shown = list(dict.fromkeys(card["type"] for card in cards))
    domain = sorted(
        (entity_type for entity_type in shown if entity_type not in SCHEMA_TYPES),
        key=lambda entity_type: -_count_statuses(reader, entity_type),
    )
    schema = [entity_type for entity_type in shown if entity_type in SCHEMA_TYPES]
    return {
        "domain": [_describe_type(reader, entity_type, cards) for entity_type in domain],
        "schema": [_describe_type(reader, entity_type, cards) for entity_type in schema],
    }
