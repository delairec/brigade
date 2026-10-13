import json
import re
from pathlib import Path

from brigade.corpus.format_and_lint_file import format_and_lint_file
from brigade.corpus.run_awawa import run_awawa
from brigade.runtime import Runtime
from brigade.system.write_text_file import write_text_file

SCHEMA_TYPE = "SCHEMA"
SCHEMA_TYPE_PATTERN = re.compile(r'^SCHEMA (\S+)\n(?:\t.*\n)*?\tDESC (".*")$', re.MULTILINE)
COMMENT = "//"
SCHEMA_KEYWORD = "SCHEMA "


def _read_schema_types(schema: str) -> list[tuple[str, str]]:
    return [(name, json.loads(description)) for name, description in SCHEMA_TYPE_PATTERN.findall(schema)]


def _run_awawa(runtime: Runtime, path: Path, arguments: tuple[str, ...]) -> str:
    return run_awawa(runtime.run_process, path.parent, arguments).stdout


def _show_command(runtime: Runtime, path: Path, arguments: tuple[str, ...]) -> str:
    return f"$ awawa {' '.join(arguments)}\n{_run_awawa(runtime, path, arguments)}"


def _list_entities(runtime: Runtime, path: Path) -> list[dict]:
    status = json.loads(_run_awawa(runtime, path, ("status", "--json", str(path))))
    entities = [entity for entity in status["entities"] if entity["type"] != SCHEMA_TYPE]
    return sorted(entities, key=lambda entity: entity["line"])


def _holds_entry_line(line: str) -> bool:
    return bool(line.strip()) and not line[0].isspace() and not line.startswith((COMMENT, SCHEMA_KEYWORD))


def _describe_lint_failure(path: Path, output: str) -> str:
    return (
        f"$ awawa lint --strict {path}\n{output}\n\n"
        f"Rewrite {path} so that awawa lint --strict {path} passes, keeping every entry. The file as it is:\n\n"
        f"{path.read_text(encoding='utf-8')}"
    )


def _read_entity(runtime: Runtime, path: Path, entity: dict) -> dict:
    target = f"@{entity['type']}.{entity['name']}"
    shown = json.loads(_run_awawa(runtime, path, ("show", target, "--json", str(path))))
    fields = [
        {"name": field["name"], "value": "".join(json.loads(atom) for atom in field["atoms"])}
        for field in shown["fields"]
    ]
    return {"type": entity["type"], "name": entity["name"], "fields": fields}


def _render_entity(entity: dict) -> str:
    fields = "".join(f"  {field['name']}: {field['value']}\n" for field in entity["fields"])
    return f"{entity['type']} {entity['name']}\n{fields}"


def create_document(request: dict, runtime: Runtime) -> None:
    write_text_file(Path(request["path"]), request["schema"])


def describe_document(request: dict, runtime: Runtime) -> dict:
    path = request["path"]
    types = "".join(f"- {name}: {description}\n" for name, description in _read_schema_types(request["schema"]))
    frame = "".join(f"- {line}\n" for line in request["frame"])
    text = (
        f"The {request['document']} is the awawa corpus {path}: after the schema it holds, append one entity per"
        " entry, of a type the schema declares, named by the initial of its type in lower case and its rank among"
        f" the entities of that type in order of writing.\n\n{types}\n{frame}"
    )
    if request["shell"]:
        text += (
            f"\nAfter each append, run awawa fmt {path} then awawa lint --strict {path}, naming the file and never"
            " its directory.\n"
        )
    return {"text": text}


def read_document(request: dict, runtime: Runtime) -> dict:
    path = Path(request["path"])
    report = format_and_lint_file(runtime.run_process, path)
    if not report.clean:
        return {"text": _describe_lint_failure(path, report.output)}
    inventories = [
        _show_command(runtime, path, ("status", name, str(path))) for name, _ in _read_schema_types(request["schema"])
    ]
    last = _list_entities(runtime, path)[-1]
    shown = _show_command(runtime, path, ("show", f"@{last['type']}.{last['name']}", str(path)))
    return {"text": "\n".join([*inventories, shown])}


def detect_entry(request: dict, runtime: Runtime) -> dict:
    lines = Path(request["path"]).read_text(encoding="utf-8").splitlines()
    return {"holds_entry": any(_holds_entry_line(line) for line in lines)}


def render_document(request: dict, runtime: Runtime) -> dict:
    path = Path(request["path"])
    entities = [_read_entity(runtime, path, entity) for entity in _list_entities(runtime, path)]
    return {"text": "\n".join(_render_entity(entity) for entity in entities), "entities": entities}
