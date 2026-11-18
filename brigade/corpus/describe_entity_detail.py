from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.describe_entity_card import describe_entity_card


def _describe_neighbour(reader: CorpusReader, target: str) -> dict:
    card = describe_entity_card(reader, reader.row(target))
    return {"target": target, "code": card["code"], "label": card["label"], "status": card["status"]}


def _read_targets(entities: list[dict]) -> list[str]:
    return [f"@{entity['type']}.{entity['name']}" for entity in entities]


def describe_entity_detail(reader: CorpusReader, target: str) -> dict:
    context = reader.read_context(target)
    references = _read_targets(context["frontier"])
    referring_back = [other for other in references if target in _read_targets(reader.read_context(other)["frontier"])]
    referencing = [*_read_targets(context["referenced_by"]), *referring_back]
    return {
        "entity": reader.show(target),
        "references": [_describe_neighbour(reader, other) for other in references],
        "referenced_by": [_describe_neighbour(reader, other) for other in dict.fromkeys(referencing)],
    }
