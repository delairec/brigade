from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.set_entity_status import set_entity_status
from brigade.runtime import Runtime
from brigade.studies.name_answer_file import name_answer_file
from brigade.triage.dismiss_cited_signals import dismiss_cited_signals
from brigade.triage.read_new_pattern import PATTERN_TYPE, read_new_pattern

DISMISSED_STATUS = "dismissed"


def dismiss_pattern(runtime: Runtime, name: str) -> None:
    root = runtime.paths.config_root
    patterns = []

    def rewrite(texts: tuple[str, ...]) -> tuple[str, ...]:
        patterns.append(read_new_pattern(runtime, name))
        return (set_entity_status(texts[0], PATTERN_TYPE, name, DISMISSED_STATUS),)

    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(name_answer_file(PATTERN_TYPE),),
            describe_message=lambda: f"brigade inbox dismiss: @{PATTERN_TYPE}.{name} {DISMISSED_STATUS}",
            rewrite=rewrite,
        ),
    )
    dismiss_cited_signals(runtime, patterns[0])
