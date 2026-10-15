import json

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.errors import BrigadeError
from brigade.studies.render_answer import render_answer
from brigade.studies.study_run_context import ANSWER_FILE, STEPS_DIRECTORY, StudyRunContext
from brigade.system.write_text_atomically import write_text_atomically

ENTITY_OUTPUT_PREFIX = "entity:"
COLLECT_STEP_FILE = "collect.json"


def _append_block(text: str, block: str) -> str:
    if not text.strip():
        return block
    return text.rstrip("\n") + "\n\n" + block


def _read_answer(context: StudyRunContext) -> str:
    answer_path = context.run_directory / ANSWER_FILE
    if answer_path.is_file():
        return answer_path.read_text(encoding="utf-8")
    collected = json.loads((context.run_directory / STEPS_DIRECTORY / COLLECT_STEP_FILE).read_text(encoding="utf-8"))
    answer = render_answer(context, collected["collected"])
    write_text_atomically(answer_path, answer)
    return answer


def _write_entity(context: StudyRunContext, answer: str) -> None:
    root = context.runtime.paths.config_root
    file_name = f"{context.study.answer_type.lower()}s.awawa"
    change_corpus_file(
        context.runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(context.runtime.paths.lock_directory, root),
            file_names=(file_name,),
            describe_message=lambda: f"brigade study run: the answer of @STUDY.{context.study.name}",
            rewrite=lambda texts: (_append_block(texts[0], answer),),
        ),
    )


def write_answer(context: StudyRunContext) -> dict:
    output = context.study.output
    if not output.startswith(ENTITY_OUTPUT_PREFIX):
        raise BrigadeError(f"the output {output} is not written by this brigade")
    _write_entity(context, _read_answer(context))
    return {"output": output, "answer": str(context.run_directory / ANSWER_FILE)}
