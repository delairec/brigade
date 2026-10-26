def append_entity_block(text: str, block: str) -> str:
    if not text.strip():
        return block
    return text.rstrip("\n") + "\n\n" + block
