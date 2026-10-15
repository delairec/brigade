from dataclasses import dataclass

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.runtime import Runtime

STUDIES_FILE = "studies.awawa"
ACTIVE_STATUS = "active"


@dataclass(frozen=True)
class NewStudy:
    name: str
    title: str
    question: str | None
    project: str | None
    collectors: tuple[str, ...]
    slot: str
    every: str | None
    output: str
    answer_type: str


def _render_block(study: NewStudy) -> str:
    lines = [f"STUDY {study.name}", f"\tTITLE {quote_awawa_string(study.title)}"]
    if study.question is not None:
        lines.append(f"\tQUESTION {quote_awawa_string(study.question)}")
    if study.project is not None:
        lines.append(f"\tPROJECT @PROJECT.{study.project}")
    lines.extend(f"\tCOLLECTOR {quote_awawa_string(collector)}" for collector in study.collectors)
    lines.append(f"\tSLOT {study.slot}")
    if study.every is not None:
        lines.append(f"\tEVERY {quote_awawa_string(study.every)}")
    lines.append(f"\tOUTPUT {quote_awawa_string(study.output)}")
    lines.append(f"\tANSWER {quote_awawa_string(study.answer_type)}")
    lines.append(f"\tSTATUS {ACTIVE_STATUS}")
    return "\n".join(lines) + "\n"


def _append_block(text: str, block: str) -> str:
    if not text.strip():
        return block
    return text.rstrip("\n") + "\n\n" + block


def record_study(runtime: Runtime, study: NewStudy) -> None:
    root = runtime.paths.config_root
    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(STUDIES_FILE,),
            describe_message=lambda: f"brigade study new: @STUDY.{study.name}",
            rewrite=lambda texts: (_append_block(texts[0], _render_block(study)),),
        ),
    )
