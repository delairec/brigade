from brigade.system.ask_configured_client import ConfiguredClientAnswer
from brigade.system.describe_client_answered import describe_client_answered
from brigade.system.describe_slot_clients import describe_slot_clients


def describe_configured_client_answer(answer: ConfiguredClientAnswer) -> list[str]:
    return [describe_client_answered(answer.client), *describe_slot_clients(answer.slot_clients)]
