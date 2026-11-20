from brigade.corpus.corpus_reader import STATUS_FIELD, CorpusReader
from brigade.corpus.describe_board_view import describe_board_view
from brigade.corpus.describe_dependencies_view import describe_dependencies_view
from brigade.corpus.describe_entity_detail import describe_entity_detail
from brigade.corpus.describe_health_view import describe_health_view
from brigade.corpus.describe_tree_view import describe_tree_view
from brigade.corpus.select_view_cards import select_view_cards
from brigade.corpus.view_request import ViewRequest
from brigade.errors import BrigadeError

__all__ = ("ViewRequest", "describe_view_document")


def _name_dependency_fields(reader: CorpusReader, entity_type: str) -> list[str]:
    return [field.name for field in reader.fields(entity_type) if field.referred == (entity_type,)]


def _select_dependency_field(fields: list[str], entity_type: str) -> str:
    if not fields:
        raise BrigadeError(f"{entity_type} has no field referring to entities of its own type")
    return fields[0]


def _describe_view(reader: CorpusReader, request: ViewRequest) -> dict:
    if request.view == "health":
        return describe_health_view(reader, request.search)
    if request.entity_type is not None and not reader.rows_of(request.entity_type):
        raise BrigadeError(f"the corpus holds no entity of type {request.entity_type}")
    if request.view == "tree":
        if request.filters and request.entity_type is None:
            raise BrigadeError("--filter reads the entities of --type")
        types = dict.fromkeys(row.type for row in reader.rows)
        rows = [row for entity_type in types for row in reader.rows_of(entity_type)]
        cards = select_view_cards(reader, rows, request)
        return describe_tree_view(reader, cards)
    if request.entity_type is None:
        raise BrigadeError(f"--view {request.view} reads the entities of --type")
    rows = reader.rows_of(request.entity_type)
    cards = select_view_cards(reader, rows, request)
    if request.view == "board":
        fields = [field.name for field in reader.fields(request.entity_type)]
        board = describe_board_view(reader, cards, request.entity_type, request.field or STATUS_FIELD)
        return board | {"fields": fields}
    fields = _name_dependency_fields(reader, request.entity_type)
    field = request.field or _select_dependency_field(fields, request.entity_type)
    return describe_dependencies_view(reader, cards, field) | {"fields": fields}


def describe_view_document(reader: CorpusReader, request: ViewRequest) -> dict:
    document = {"view": request.view, **_describe_view(reader, request)}
    if request.entity is not None:
        document["detail"] = describe_entity_detail(reader, request.entity)
    return document
