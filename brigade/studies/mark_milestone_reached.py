from pathlib import Path

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.corpus.read_entities import Entity
from brigade.corpus.set_entity_status import set_entity_status
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.runtime import Runtime

MILESTONE_TYPE = "MILESTONE"
REACHED_STATUS = "reached"


def mark_milestone_reached(runtime: Runtime, checkout: Path, project: Entity, milestone: str) -> None:
    workspace = read_corpus_workspace(project)
    shown = read_awawa_document(runtime.run_process, checkout / workspace, ("show", f"@{MILESTONE_TYPE}.{milestone}"))
    file_name = str(Path(shown["file"]).relative_to(checkout))
    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=checkout,
            lock=locate_corpus_lock(runtime.paths.lock_directory, checkout),
            file_names=(file_name,),
            describe_message=lambda: f"docs(corpus): mark @{MILESTONE_TYPE}.{milestone} {REACHED_STATUS}",
            rewrite=lambda texts: (set_entity_status(texts[0], MILESTONE_TYPE, milestone, REACHED_STATUS),),
            workspace=workspace,
        ),
    )
