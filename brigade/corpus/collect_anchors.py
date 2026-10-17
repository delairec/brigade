import json

ANCHOR_FIELD = "IMPL"


def collect_anchors(fields: list) -> list[str]:
    return [
        anchor
        for field in fields
        for anchor in (
            [json.loads(field["atoms"][0])] if field["name"] == ANCHOR_FIELD else collect_anchors(field["fields"])
        )
    ]
