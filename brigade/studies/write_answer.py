from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.studies.choose_answer_form import choose_answer_form
from brigade.studies.choose_answer_publisher import choose_answer_publisher
from brigade.studies.fold_pattern_answer import FoldedAnswer
from brigade.studies.name_answer_file import name_answer_file
from brigade.studies.present_answer import present_answer
from brigade.studies.read_collected import read_collected
from brigade.studies.record_scan_signals import record_scan_signals
from brigade.studies.render_answer import render_answer
from brigade.studies.study_run_context import ANSWER_FILE, StudyRunContext
from brigade.system.write_text_atomically import write_text_atomically

ENTITY_OUTPUT_PREFIX = "entity:"
SCAN = ("none", "inbox")


def _append_block(text: str, block: str) -> str:
    if not block.strip():
        return text
    if not text.strip():
        return block
    return text.rstrip("\n") + "\n\n" + block


def _append_folded(folded: FoldedAnswer) -> str:
    return _append_block(folded.held, folded.new)


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
            rewrite=lambda texts: (_append_folded(choose_answer_form(context.study).fold(texts[0], answer)),),
        ),
    )


def write_answer(context: StudyRunContext) -> dict:
    output = context.study.output
    answer = _read_answer(context)
    written = {"output": output, "answer": str(context.run_directory / ANSWER_FILE)}
    if (context.study.slot, output) == SCAN:
        return {**written, **record_scan_signals(context)}
    if output.startswith(ENTITY_OUTPUT_PREFIX):
        _write_entity(context, answer)
        return {**written, **choose_answer_form(context.study).publish(context)}
    return {**written, **choose_answer_publisher(output)(context, present_answer(context))}
