from brigade.corpus.decode_atom import decode_atom

ANCHOR_FIELD = "IMPL"


def collect_anchors(fields: list) -> list[str]:
    return [
        anchor
        for field in fields
        for anchor in (
            [decode_atom(field["atoms"][0])] if field["name"] == ANCHOR_FIELD else collect_anchors(field["fields"])
        )
    ]
