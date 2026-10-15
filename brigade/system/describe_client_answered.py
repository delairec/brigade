NO_CLIENT = "no client"


def describe_client_answered(client: str | None) -> str:
    return f"answers for {NO_CLIENT if client is None else client}"
