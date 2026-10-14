from dataclasses import dataclass

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.ledger.format_instant import format_instant
from brigade.runtime import Runtime
from brigade.waves.name_next_request import name_next_request

REQUESTS_FILE = "requests.awawa"
PLANNING_STATUS = "planning"


@dataclass(frozen=True)
class NewRequest:
    project: str
    text: str


def _render_block(name: str, new_request: NewRequest, created_at: str) -> str:
    return (
        f"REQUEST {name}\n"
        f"\tPROJECT @PROJECT.{new_request.project}\n"
        f"\tTEXT {quote_awawa_string(new_request.text)}\n"
        f"\tCREATED_AT {quote_awawa_string(created_at)}\n"
        f"\tSTATUS {PLANNING_STATUS}\n"
    )


def _append_block(text: str, block: str) -> str:
    if not text.strip():
        return block
    return text.rstrip("\n") + "\n\n" + block


def record_request(runtime: Runtime, new_request: NewRequest) -> str:
    root = runtime.paths.config_root
    names = []

    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        name = name_next_request(texts[0], new_request.project)
        names.append(name)
        return (_append_block(texts[0], _render_block(name, new_request, format_instant(runtime.now))),)

    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(REQUESTS_FILE,),
            describe_message=lambda: f"brigade wave new: @REQUEST.{names[0]} of @PROJECT.{new_request.project}",
            rewrite=rewrite,
        ),
    )
    return names[0]
