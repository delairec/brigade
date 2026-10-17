import argparse
import re

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.read_entities import read_entities
from brigade.errors import BrigadeError
from brigade.ledger.append_derived_event import append_derived_event
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.wave_started import WaveStarted
from brigade.planning.locate_request_file import locate_request_file
from brigade.runtime import Runtime
from brigade.system.read_configuration import Configuration
from brigade.waves.describe_request import describe_request
from brigade.waves.mark_request_running import RUNNING_STATUS, mark_request_running
from brigade.waves.name_next_wave import name_next_wave
from brigade.waves.read_wave_request import ENTITY_TYPE, read_wave_request

PLANNED_STATUS = "planned"
TASK_TYPE = "TASK"
TASK_NUMBER = re.compile(r"\d+$")


def _read_task_number(task: str) -> int:
    return int(TASK_NUMBER.search(task).group())


def _list_wave_tasks(runtime: Runtime, configuration: Configuration, request: dict) -> tuple[str, ...]:
    query = argparse.Namespace(project=request["project"], ref=request["branch"], worktree=None)
    tree = prepare_project_tree(query, configuration, runtime)
    tasks = read_entities(runtime.run_process, tree.root, TASK_TYPE, f"MILESTONE==@MILESTONE.{request['milestone']}")
    return tuple(sorted((task.name for task in tasks), key=_read_task_number))


def start_wave(runtime: Runtime, configuration: Configuration, name: str) -> dict:
    request = describe_request(read_wave_request(runtime, name))
    if request["status"] != PLANNED_STATUS:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is {request['status']}, not {PLANNED_STATUS}")
    tasks = _list_wave_tasks(runtime, configuration, request)
    root = runtime.paths.config_root

    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        return (mark_request_running(texts[0], name),)

    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(locate_request_file(runtime, name),),
            describe_message=lambda: f"brigade wave start: @{ENTITY_TYPE}.{name} {RUNNING_STATUS}",
            rewrite=rewrite,
        ),
    )

    def name_wave(reading: LedgerReading) -> WaveStarted:
        return WaveStarted(
            wave=name_next_wave(request["project"], tuple(entry.event for entry in reading.entries)),
            project=request["project"],
            branch=request["branch"],
            tasks=tasks,
        )

    started = append_derived_event(runtime.paths, runtime.now, name_wave)
    return {
        "request": name,
        "status": RUNNING_STATUS,
        "wave": started["wave"],
        "milestone": request["milestone"],
        "project": request["project"],
    }
