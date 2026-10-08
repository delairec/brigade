from brigade.runtime import Runtime
from brigade.system.ask_client import ClientQuestion, ask_client
from brigade.system.read_configuration import Configuration


def ask_named_client(client, question: ClientQuestion, configuration: Configuration, runtime: Runtime) -> dict:
    completed_request = {
        **question.request,
        "reasoning_table": {
            level: {"model": row.model, "effort": row.effort} for level, row in configuration.reasoning.items()
        },
        "settings": configuration.clients.get(question.client_name, {}),
        "home": str(runtime.paths.home),
    }
    completed_question = ClientQuestion(
        client_name=question.client_name, operation=question.operation, request=completed_request
    )
    return ask_client(client, completed_question)
