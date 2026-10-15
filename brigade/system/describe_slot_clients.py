def describe_slot_clients(slot_clients: dict) -> list[str]:
    return [f"slot {slot} runs on {client}" for slot, client in slot_clients.items()]
