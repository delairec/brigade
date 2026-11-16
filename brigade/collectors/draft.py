import json
import re
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.read_entities import Entity, EntityField, read_entities
from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.errors import BrigadeError
from brigade.git.map_cited_lines import map_cited_lines
from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.runtime import Runtime
from brigade.system.run_process import ProcessRequest
from brigade.tasks.read_task_after import read_task_after

NAME = "draft"
TASK_PARAMETER = "task"
TASK_TYPE = "TASK"
LIVE_TASKS = ("STATUS!=implemented", "STATUS!=archived")
DELIVERABLE_FIELDS = ("TITLE", "SPEC")
SOURCE_FIELD = "SOURCE"
STATUS_FIELD = "STATUS"
FRESH_AT_EACH_CALL = False
FILE_CITATION = re.compile(
    r"(?<![\w./@-])((?:[\w-]+/)*[\w-]*[A-Za-z][\w-]*\.[a-z][a-z0-9]{0,4})(?![\w-])(?::(\d+)(?:-(\d+))?)?"
)
ENTITY_CITATION = re.compile(r"@[A-Z][A-Z_]*\.\w+")
BLAME_HEADER = re.compile(r"([0-9a-f]{40}) ")
COMMITTER_TIME = "committer-time "


def _run_git(runtime: Runtime, root: Path, arguments: tuple[str, ...]) -> str:
    request = ProcessRequest(
        argv=("git", *arguments), cwd=str(root), timeout_s=GIT_TIMEOUT_S, acceptable_exit_codes=SUCCESS
    )
    return runtime.run_process(request).stdout


def _show(runtime: Runtime, root: Path, target: str) -> dict:
    return json.loads(run_awawa(runtime.run_process, root, ("show", target, "--json", str(root)), SUCCESS).stdout)


def _read_field(entity: Entity, name: str) -> str:
    return next(field.value for field in entity.fields if field.name == name)


def _join_deliverables(entity: Entity) -> str:
    return "\n".join(field.value for field in entity.fields if field.name in DELIVERABLE_FIELDS)


def _list_files(text: str) -> list[str]:
    return sorted({citation.group(1) for citation in FILE_CITATION.finditer(text)})


def _list_entities(text: str) -> list[str]:
    return sorted(set(ENTITY_CITATION.findall(text)))


def _find_source_commit(runtime: Runtime, root: Path, task: str, file: str) -> str:
    entity = next(entity for entity in _show(runtime, root, file)["entities"] if entity["name"] == task)
    lines = [line["line"] for line in entity["lines"] if line["field_path"][:1] == [SOURCE_FIELD]]
    if not lines:
        raise BrigadeError(f"@{TASK_TYPE}.{task} has no SOURCE: its citations have no commit to be read at")
    blame = _run_git(runtime, root, ("blame", "--porcelain", "-L", f"{min(lines)},{max(lines)}", "HEAD", "--", file))
    times = {}
    commit = None
    for line in blame.splitlines():
        header = BLAME_HEADER.match(line)
        if header:
            commit = header.group(1)
        elif line.startswith(COMMITTER_TIME):
            times[commit] = int(line.removeprefix(COMMITTER_TIME))
    return max(times, key=times.get)


def _describe_citations(runtime: Runtime, root: Path, text: str, source_commit: str) -> list[dict]:
    citations = []
    for citation in FILE_CITATION.finditer(text):
        if citation.group(2) is None:
            continue
        path = citation.group(1)
        start = int(citation.group(2))
        end = int(citation.group(3) or start)
        diff = _run_git(runtime, root, ("diff", "-U0", source_commit, "HEAD", "--", path))
        now = map_cited_lines(diff, start, end)
        citations.append(
            {
                "citation": citation.group(0),
                "path": path,
                "start": start,
                "end": end,
                "now": None if now is None else {"start": now[0], "end": now[1]},
            }
        )
    return citations


def _describe_task(task: Entity) -> dict:
    deliverables = _join_deliverables(task)
    return {
        "task": task.name,
        "status": _read_field(task, STATUS_FIELD),
        "files": _list_files(deliverables),
        "entities": _list_entities(deliverables),
    }


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    root = inputs.project
    name = inputs.parameters[TASK_PARAMETER]
    shown = _show(runtime, root, f"@{TASK_TYPE}.{name}")
    draft = Entity(
        name=name,
        fields=tuple(
            EntityField(name=field["name"], value="".join(map(decode_atom, field["atoms"])))
            for field in shown["fields"]
        ),
    )
    source_commit = _find_source_commit(runtime, root, name, shown["file"])
    deliverables = _join_deliverables(draft)
    whole_text = "\n".join(field.value for field in draft.fields)
    summary = {
        "task": name,
        "after": list(read_task_after(draft)),
        "source_commit": source_commit,
        "files": _list_files(deliverables),
        "entities": _list_entities(deliverables),
        "citations": _describe_citations(runtime, root, whole_text, source_commit),
    }
    tasks = [
        _describe_task(task)
        for task in read_entities(runtime.run_process, root, TASK_TYPE, *LIVE_TASKS)
        if task.name != name
    ]
    return {**describe_collection(NAME, runtime, summary, tasks), "cache": FRESH_AT_EACH_CALL}
