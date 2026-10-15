from brigade.system.read_configuration import Configuration


def list_slot_clients_elsewhere(configuration: Configuration, client: str | None) -> dict:
    return {slot: bound for slot, bound in configuration.slot_clients.items() if bound != client}
