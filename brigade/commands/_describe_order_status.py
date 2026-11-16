def describe_order_status(document: dict, done: str) -> str:
    target = f"@ORDER.{document['order']}"
    if document["changed"]:
        return f"{done} {target}"
    return f"{target} is already {document['status']}"
