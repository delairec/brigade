from brigade.errors import BrigadeError
from brigade.system.actions_answer import ActionsAnswer
from brigade.system.client_command import ClientCommand
from brigade.system.client_question import ClientQuestion
from brigade.system.client_shapes import CLIENT_ANSWER_SHAPES
from brigade.system.parse_result_answer import ParseResultAnswer
from brigade.system.probe_answer import ProbeAnswer
from brigade.system.transcripts_answer import TranscriptsAnswer
from brigade.system.validate_document import DocumentInvalid, validate_document

ANSWER_KINDS = {
    "probe": ProbeAnswer,
    "launch-argv": ClientCommand,
    "resume-argv": ClientCommand,
    "parse-result": ParseResultAnswer,
    "transcripts": TranscriptsAnswer,
    "actions": ActionsAnswer,
}


def read_client_answer(
    question: ClientQuestion, answer
) -> ProbeAnswer | ClientCommand | ParseResultAnswer | TranscriptsAnswer | ActionsAnswer:
    operation = question.request.operation
    try:
        validate_document(answer, CLIENT_ANSWER_SHAPES[operation])
    except DocumentInvalid as problem:
        raise BrigadeError(f"client adapter {question.client_name} answered {operation}: {problem}") from None
    return ANSWER_KINDS[operation].from_document(answer)
