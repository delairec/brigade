import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.collector_environment import CollectorInputs, create_collector_environment
from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.collector_shapes import COLLECTOR_DOCUMENT_SHAPE
from brigade.collecting.read_cache_input import read_cache_input
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.validate_document import DocumentInvalid, validate_document
from brigade.system.write_json_atomically import write_json_atomically
from brigade.system.write_text_atomically import write_text_atomically

CACHE_DIRECTORY = "collectors"
RUN_DIRECTORY = "collect"
DOCUMENT_FILE = "document.json"
SIDECAR_FILE = "sidecar.json"
SIDECAR_SCHEMA_VERSION = 1
COMPLETE_EXIT_CODE = 0
STDERR_TAIL_LINES = 20
NO_REASON = ""
CACHE_DECLARATION = "cache"
NOT_CACHED = False


@dataclass(frozen=True)
class CollectionRequest:
    inputs: CollectorInputs
    refresh: bool
    equipment: CollectorEquipment


@dataclass(frozen=True)
class Collection:
    document_path: Path
    document: dict
    cached: bool


def _describe_failure(name: str, answer, reason: str) -> BrigadeError:
    tail = answer.stderr.splitlines()[-STDERR_TAIL_LINES:]
    return BrigadeError("\n".join([f"collector {name} exited {answer.exit_code}{reason}", *tail]))


def _read_answer(name: str, answer) -> dict:
    if answer.exit_code != COMPLETE_EXIT_CODE:
        raise _describe_failure(name, answer, NO_REASON)
    try:
        document = json.loads(answer.stdout)
    except ValueError:
        raise _describe_failure(name, answer, ": it printed no JSON document") from None
    try:
        validate_document(document, COLLECTOR_DOCUMENT_SHAPE)
    except DocumentInvalid as error:
        raise _describe_failure(name, answer, f": its document {error}") from None
    return document


def _compute_cache_key(collector, inputs: CollectorInputs, cache_input) -> str:
    material = {
        "command": collector.command,
        "parameters": inputs.parameters,
        "since": inputs.since.isoformat(),
        "input": cache_input,
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def _collect_afresh(collector, request: CollectionRequest, key: str, runtime: Runtime) -> dict:
    inputs = request.inputs
    answer = collector.collect(create_collector_environment(inputs), runtime, request.equipment)
    return {
        DOCUMENT_FILE: _read_answer(collector.name, answer),
        SIDECAR_FILE: {
            "schema_version": SIDECAR_SCHEMA_VERSION,
            "collector": collector.name,
            "command": collector.command,
            "parameters": inputs.parameters,
            "since": inputs.since.isoformat(),
            "duration_ms": answer.duration_ms,
            "exit_code": answer.exit_code,
            "cache_key": key,
        },
    }


def _write_files(place: Path, files: dict) -> None:
    for file_name, content in files.items():
        write_json_atomically(place / file_name, content)


def _place(entry: Path, name: str, run_directory: Path | None) -> Path:
    if run_directory is None:
        return entry
    place = run_directory / RUN_DIRECTORY / name
    for file_name in (DOCUMENT_FILE, SIDECAR_FILE):
        write_text_atomically(place / file_name, (entry / file_name).read_text(encoding="utf-8"))
    return place


def collect_document(collector: object, request: CollectionRequest, runtime: Runtime) -> Collection:
    inputs = request.inputs
    key = _compute_cache_key(collector, inputs, read_cache_input(collector.name, inputs.project, runtime))
    entry = runtime.paths.cache_root / CACHE_DIRECTORY / collector.name / key
    cached = not request.refresh and (entry / DOCUMENT_FILE).is_file()
    if not cached:
        files = _collect_afresh(collector, request, key, runtime)
        if not files[DOCUMENT_FILE].get(CACHE_DECLARATION, NOT_CACHED):
            place = (runtime.paths.run_directory or runtime.paths.state_root) / RUN_DIRECTORY / collector.name
            _write_files(place, files)
            return Collection(document_path=place / DOCUMENT_FILE, document=files[DOCUMENT_FILE], cached=False)
        _write_files(entry, files)
    place = _place(entry, collector.name, runtime.paths.run_directory)
    document = json.loads((place / DOCUMENT_FILE).read_text(encoding="utf-8"))
    return Collection(document_path=place / DOCUMENT_FILE, document=document, cached=cached)
