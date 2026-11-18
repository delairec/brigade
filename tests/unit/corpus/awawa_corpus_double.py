import json
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.unit.commands.command_runtime import answer

STRING = {"kind": "string", "label": "string"}
UINT = {"kind": "uint", "label": "uint"}
LINT_IN_ERROR = 1
NOT_DEFINED = 1


@dataclass(frozen=True)
class FakeEntity:
    type: str
    name: str
    status: str | None
    fields: tuple[tuple[str, tuple[str, ...]], ...] = ()
    line: int = 1
    file: str = "corpus/tasks.awawa"


@dataclass(frozen=True)
class FakeCorpus:
    entities: tuple[FakeEntity, ...]
    schemas: dict
    diagnostics: tuple[dict, ...] = ()
    unresolved: int = 0


def declare_field(name: str, *alternatives: dict, required: bool = False, repeatable: bool = False) -> dict:
    return {"name": name, "required": required, "repeatable": repeatable, "slots": [list(alternatives)]}


def declare_literals(*values: str) -> list[dict]:
    return [{"kind": "literal", "label": value, "value": value} for value in values]


def declare_reference(entity_type: str) -> dict:
    return {"kind": "ref", "label": f"@{entity_type}", "type": entity_type}


def _target(entity: FakeEntity) -> str:
    return f"@{entity.type}.{entity.name}"


def _shown_fields(entity: FakeEntity) -> list[dict]:
    status = [] if entity.status is None else [("STATUS", (entity.status,))]
    return [{"name": name, "atoms": list(atoms), "fields": []} for name, atoms in [*status, *entity.fields]]


def _references(entity: FakeEntity) -> list[str]:
    atoms = [atom for _, written in entity.fields for atom in written if atom.startswith("@")]
    return list(dict.fromkeys(atoms))


def _describe_row(entity: FakeEntity, root: Path) -> dict:
    return {
        "type": entity.type,
        "name": entity.name,
        "target": _target(entity),
        "file": str(root / entity.file),
        "line": entity.line,
        "status": entity.status,
    }


def _answer_status(corpus: FakeCorpus, root: Path) -> dict:
    types = list(dict.fromkeys(entity.type for entity in corpus.entities))
    severities = [diagnostic["severity"] for diagnostic in corpus.diagnostics]
    return {
        "types": [{"type": entity_type} for entity_type in types],
        "entities": [_describe_row(entity, root) for entity in corpus.entities],
        "references": {"unresolved": corpus.unresolved},
        "diagnostics": {"errors": severities.count("error"), "warnings": severities.count("warning")},
    }


def _answer_context(corpus: FakeCorpus, root: Path, entity: FakeEntity) -> dict:
    referring = [
        other for other in corpus.entities for _, atoms in other.fields for atom in atoms if atom == _target(entity)
    ]
    return {
        "entities": [_describe_row(entity, root) | {"depth": 0, "fields": _shown_fields(entity)}],
        "resolved": {entity.type: {"fields": corpus.schemas[entity.type]}} if entity.type in corpus.schemas else {},
        "frontier": [
            {"type": target[1:].partition(".")[0], "name": target.partition(".")[2]} for target in _references(entity)
        ],
        "referenced_by": [
            {"type": other.type, "name": other.name, "target": _target(entity), "converse": None} for other in referring
        ],
    }


def _answer_lint(corpus: FakeCorpus, root: Path) -> tuple[dict, int]:
    diagnostics = [diagnostic | {"file": str(root / diagnostic["file"])} for diagnostic in corpus.diagnostics]
    in_error = any(diagnostic["severity"] == "error" for diagnostic in corpus.diagnostics)
    return {"diagnostics": diagnostics}, LINT_IN_ERROR if in_error else 0


def _answer(corpus: FakeCorpus, root: Path, request: ProcessRequest) -> ProcessRecord:
    command = request.argv[1]
    if command == "status":
        return answer(request, json.dumps(_answer_status(corpus, root)))
    if command == "lint":
        document, exit_code = _answer_lint(corpus, root)
        return answer(request, json.dumps(document), exit_code)
    entity = next((entity for entity in corpus.entities if _target(entity) == request.argv[2]), None)
    if entity is None:
        return answer(request, "", NOT_DEFINED, f"awawa {command}: {request.argv[2]} is not defined in the workspace")
    if command == "context":
        return answer(request, json.dumps(_answer_context(corpus, root, entity)))
    return answer(request, json.dumps(_describe_row(entity, root) | {"fields": _shown_fields(entity)}))


def create_awawa_double(corpus: FakeCorpus, root: Path):
    return lambda request: _answer(corpus, root, request)
