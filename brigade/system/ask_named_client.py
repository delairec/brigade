from brigade.runtime import Runtime
from brigade.system.actions_answer import ActionsAnswer
from brigade.system.client_command import ClientCommand
from brigade.system.client_question import ClientQuestion
from brigade.system.parse_result_answer import ParseResultAnswer
from brigade.system.probe_answer import ProbeAnswer
from brigade.system.read_client_answer import read_client_answer
from brigade.system.read_configuration import Configuration
from brigade.system.transcripts_answer import TranscriptsAnswer


def ask_named_client(
    client, question: ClientQuestion, configuration: Configuration, runtime: Runtime
) -> ProbeAnswer | ClientCommand | ParseResultAnswer | TranscriptsAnswer | ActionsAnswer:
    request = {
        **question.request.to_document(),
        "reasoning_table": {
            level: {"model": row.model, "effort": row.effort} for level, row in configuration.reasoning.items()
        },
        "settings": configuration.clients.get(question.client_name, {}),
        "home": str(runtime.paths.home),
    }
    return read_client_answer(question, client.answer(question.request.operation, request))
