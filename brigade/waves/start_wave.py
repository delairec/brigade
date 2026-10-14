from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.wave_started import WaveStarted
from brigade.planning.locate_request_file import locate_request_file
from brigade.runtime import Runtime
from brigade.waves.describe_request import describe_request
from brigade.waves.mark_request_running import RUNNING_STATUS, mark_request_running
from brigade.waves.read_wave_request import ENTITY_TYPE, read_wave_request

PLANNED_STATUS = "planned"


def start_wave(runtime: Runtime, name: str) -> dict:
    request = describe_request(read_wave_request(runtime, name))
    if request["status"] != PLANNED_STATUS:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is {request['status']}, not {PLANNED_STATUS}")
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
    append_event(runtime.paths, runtime.now, WaveStarted(wave=request["milestone"], project=request["project"]))
    return {"request": name, "status": RUNNING_STATUS, "milestone": request["milestone"], "project": request["project"]}
