from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.studies.choose_answer_form import choose_answer_form
from brigade.studies.hand_answer_to_output import hand_answer_to_output
from brigade.studies.name_answer_file import name_answer_file
from brigade.studies.open_answer_issue import open_answer_issue
from brigade.studies.present_answer import present_answer
from brigade.studies.read_collected import read_collected
from brigade.studies.record_answer_signal import record_answer_signal
from brigade.studies.render_answer import render_answer
from brigade.studies.study_run_context import ANSWER_FILE, StudyRunContext
from brigade.studies.write_answer_to_file import FILE_OUTPUT_PREFIX, write_answer_to_file
from brigade.system.write_text_atomically import write_text_atomically

ENTITY_OUTPUT_PREFIX = "entity:"
PUBLISHERS_BY_OUTPUT = {"issue": open_answer_issue, "inbox": record_answer_signal}


def _append_block(text: str, block: str) -> str:
    if not text.strip():
        return block
    return text.rstrip("\n") + "\n\n" + block


def _read_answer(context: StudyRunContext) -> str:
    answer_path = context.run_directory / ANSWER_FILE
    if answer_path.is_file():
        return answer_path.read_text(encoding="utf-8")
    answer = render_answer(context.study, context.run_id, read_collected(context.run_directory))
    write_text_atomically(answer_path, answer)
    return answer


def _write_entity(context: StudyRunContext, answer: str) -> None:
    root = context.runtime.paths.config_root
    file_name = name_answer_file(context.study.answer_type)
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


def _choose_publisher(output: str):
    if output.startswith(FILE_OUTPUT_PREFIX):
        return write_answer_to_file
    return PUBLISHERS_BY_OUTPUT.get(output, hand_answer_to_output)


def write_answer(context: StudyRunContext) -> dict:
    output = context.study.output
    answer = _read_answer(context)
    written = {"output": output, "answer": str(context.run_directory / ANSWER_FILE)}
    if output.startswith(ENTITY_OUTPUT_PREFIX):
        _write_entity(context, answer)
        return {**written, **choose_answer_form(context.study).publish(context)}
    return {**written, **_choose_publisher(output)(context, present_answer(context))}
