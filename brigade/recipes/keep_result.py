from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.runtime import Runtime

RESULTS_FILE = "results.awawa"
ENTITY_SEPARATOR = "\n\n"


def _append(held: str, result: str) -> str:
    if not held:
        return result
    return held.rstrip("\n") + ENTITY_SEPARATOR + result


def keep_result(runtime: Runtime, order: str, result: str) -> None:
    root = runtime.paths.config_root
    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(RESULTS_FILE,),
            describe_message=lambda: f"brigade order run: the result of @ORDER.{order}",
            rewrite=lambda texts: (_append(texts[0], result),),
        ),
    )
