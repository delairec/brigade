from brigade.system.ask_client import ClientQuestion, ask_client
from brigade.system.read_configuration import Configuration
from brigade.system.resolve_plugin import resolve_plugin


def ask_named_client(runtime, configuration: Configuration, question: ClientQuestion) -> dict:
    completed_request = {
        **question.request,
        "reasoning_table": {
            level: {"model": row.model, "effort": row.effort} for level, row in configuration.reasoning.items()
        },
        "settings": configuration.clients.get(question.client_name, {}),
        "home": str(runtime.paths.home),
    }
    client = resolve_plugin("client", question.client_name, runtime)
    completed_question = ClientQuestion(
        client_name=question.client_name, operation=question.operation, request=completed_request
    )
    return ask_client(client, completed_question)
