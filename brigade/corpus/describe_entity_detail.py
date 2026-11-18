from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.describe_entity_card import describe_entity_card


def _describe_neighbour(reader: CorpusReader, target: str) -> dict:
    card = describe_entity_card(reader, reader.row(target))
    return {"target": target, "code": card["code"], "label": card["label"], "status": card["status"]}


def describe_entity_detail(reader: CorpusReader, target: str) -> dict:
    context = reader.read_context(target)
    references = [f"@{entity['type']}.{entity['name']}" for entity in context["frontier"]]
    referencing = [f"@{entity['type']}.{entity['name']}" for entity in context["referenced_by"]]
    return {
        "entity": reader.show(target),
        "references": [_describe_neighbour(reader, other) for other in references],
        "referenced_by": [_describe_neighbour(reader, other) for other in dict.fromkeys(referencing)],
    }
