import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._accept_parameter import accept_parameter
from brigade.commands._read_parameters import read_parameters
from brigade.corpus.append_entity_block import append_entity_block
from brigade.corpus.check_type_declared import check_type_declared
from brigade.corpus.locate_entity_block import locate_entity_block
from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.corpus.write_corpus_files import CorpusWrite, write_corpus_files
from brigade.errors import BrigadeError
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.preflights.name_preflight_entity import name_preflight_entity
from brigade.preflights.preflight_places import CORPUS_PREFLIGHTS_FILE, PROJECT_PREFLIGHTS_DIRECTORY
from brigade.preflights.read_preflight_entity import ENTITY_TYPE, read_preflight_entity
from brigade.preflights.read_preflight_file import read_preflight_file
from brigade.preflights.run_preflight import PREFLIGHT_SUFFIX
from brigade.registry.find_project_at import find_project_at
from brigade.registry.locate_project_corpus import locate_project_corpus
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.check_places import locate_checks
from brigade.system.collector_places import locate_collectors
from brigade.system.create_directory import create_directory
from brigade.system.list_checks import list_checks
from brigade.system.list_collectors import list_collectors
from brigade.system.write_text_file import write_text_file

DOCUMENT_SCHEMA_VERSION = 1
PREFLIGHT_SCHEMA_VERSION = 1
COLLECTOR = "collector"
CHECK = "check"
STEP_LISTS = {COLLECTOR: "collectors", CHECK: "checks"}
ENTITY_FIELDS = {"collectors": "COLLECTOR", "checks": "CHECK"}
NO_PARAMETERS = {}
TOML_INDENT = "    "
ENTITY_INDENT = "\t"


@dataclass(frozen=True)
class PreflightAddition:
    project: Path
    name: str
    kind: str
    step: dict


def _render_text(document: dict) -> str:
    step = document["step"]
    return f"added the {step['kind']} {step['name']} to the preflight {document['preflight']} in {document['file']}"


def _classify_step(name: str, project: Path, runtime: Runtime) -> str:
    if name in {row["name"] for row in list_collectors(locate_collectors(project, runtime.paths))}:
        return COLLECTOR
    if name in {row["name"] for row in list_checks(locate_checks(project, runtime.paths))}:
        return CHECK
    raise BrigadeError(f"no collector and no check {name}")


def _create_preflight(name: str) -> dict:
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "name": name,
        "description": f"the custom preflight {name}",
        "collectors": [],
        "checks": [],
    }


def _add_step(preflight: dict, kind: str, step: dict) -> dict:
    steps = STEP_LISTS[kind]
    return {**preflight, steps: [*preflight[steps], step]}


def _render_toml_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _render_toml_step(step: dict) -> str:
    pairs = ", ".join(
        f"{_render_toml_value(key)} = {_render_toml_value(value)}"
        for key, value in step.get("parameters", NO_PARAMETERS).items()
    )
    table = f"{{ {pairs} }}" if pairs else "{}"
    return f"{TOML_INDENT}{{ name = {_render_toml_value(step['name'])}, parameters = {table} }},"


def _render_toml(preflight: dict) -> str:
    lines = [
        f"schema_version = {preflight['schema_version']}",
        f"name = {_render_toml_value(preflight['name'])}",
        f"description = {_render_toml_value(preflight['description'])}",
        *(
            line
            for steps in STEP_LISTS.values()
            for line in (f"{steps} = [", *map(_render_toml_step, preflight[steps]), "]")
        ),
    ]
    return "\n".join(lines) + "\n"


def _add_to_file(addition: PreflightAddition) -> Path:
    directory = addition.project / PROJECT_PREFLIGHTS_DIRECTORY
    preflight = read_preflight_file(directory, addition.name) or _create_preflight(addition.name)
    file = directory / f"{addition.name}{PREFLIGHT_SUFFIX}"
    create_directory(directory)
    write_text_file(file, _render_toml(_add_step(preflight, addition.kind, addition.step)))
    read_preflight_file(directory, addition.name)
    return file


def _render_entity(preflight: dict) -> str:
    lines = [
        f"{ENTITY_TYPE} {name_preflight_entity(preflight['name'])}",
        f"{ENTITY_INDENT}TITLE {quote_awawa_string(preflight['description'])}",
        *(
            line
            for steps, field in ENTITY_FIELDS.items()
            for step in preflight[steps]
            for line in (
                f"{ENTITY_INDENT}{field} {quote_awawa_string(step['name'])}",
                *(
                    f"{ENTITY_INDENT * 2}PARAMETER {quote_awawa_string(f'{key}={value}')}"
                    for key, value in step["parameters"].items()
                ),
            )
        ),
    ]
    return "\n".join(lines) + "\n"


def _place_block(text: str, name: str, block: str) -> str:
    lines = text.splitlines()
    span = locate_entity_block(lines, ENTITY_TYPE, name_preflight_entity(name))
    if span is None:
        return append_entity_block(text, block)
    return "\n".join([*lines[: span.start], *block.splitlines(), "", *lines[span.stop :]]).rstrip("\n") + "\n"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _add_to_corpus(addition: PreflightAddition, corpus: Path, runtime: Runtime) -> Path:
    project, name = addition.project, addition.name
    root = project / corpus
    if not check_type_declared(runtime.run_process, root, ENTITY_TYPE):
        raise BrigadeError(
            f"the corpus of the project at {project} declares no {ENTITY_TYPE}; add SCHEMA {ENTITY_TYPE} to it"
        )
    preflight = read_preflight_entity(runtime.run_process, root, name) or _create_preflight(name)
    file_name = str(corpus / CORPUS_PREFLIGHTS_FILE)
    block = _render_entity(_add_step(preflight, addition.kind, addition.step))
    text = _place_block(_read_text(project / file_name), name, block)
    write_corpus_files(
        runtime.run_process,
        CorpusWrite(repository=project, workspace=corpus, file_names=(file_name,), texts=(text,)),
    )
    return project / file_name


def preflight_add(request: argparse.Namespace, runtime: Runtime) -> dict:
    project = locate_main_checkout(runtime.run_process, locate_worktree_root(runtime.run_process, Path.cwd()))
    corpus = locate_project_corpus(find_project_at(read_projects(runtime), project))
    step = {"name": request.step, "parameters": read_parameters(request.extra_arguments)}
    addition = PreflightAddition(
        project=project, name=request.name, kind=_classify_step(request.step, project, runtime), step=step
    )
    file = _add_to_file(addition) if corpus is None else _add_to_corpus(addition, corpus, runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "preflight": request.name,
        "step": {"kind": addition.kind, **step},
        "file": str(file),
    }


COMMAND = Command(
    path=("preflight", "add"),
    help="add a collector or a check, key=value pairs its parameters, to a custom preflight of the project",
    arguments=(
        Argument(("name",), {"help": "the name of the custom preflight, created when the project holds none"}),
        Argument(("step",), {"help": "the name of the collector or the check to add"}),
    ),
    run=preflight_add,
    render_text=_render_text,
    accept_extra_argument=accept_parameter,
)
