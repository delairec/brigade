from collections.abc import Callable

from brigade.studies.hand_answer_to_output import hand_answer_to_output
from brigade.studies.open_answer_issue import open_answer_issue
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.record_answer_signal import record_answer_signal
from brigade.studies.study_run_context import StudyRunContext
from brigade.studies.write_answer_to_file import FILE_OUTPUT_PREFIX, write_answer_to_file

PUBLISHERS_BY_OUTPUT = {"issue": open_answer_issue, "inbox": record_answer_signal}


def choose_answer_publisher(output: str) -> Callable[[StudyRunContext, AnswerPublication], dict]:
    if output.startswith(FILE_OUTPUT_PREFIX):
        return write_answer_to_file
    return PUBLISHERS_BY_OUTPUT.get(output, hand_answer_to_output)
