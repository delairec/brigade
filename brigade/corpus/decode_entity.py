from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.entity import Entity, EntityField


def decode_entity(name: str, shown: dict) -> Entity:
    fields = tuple(
        EntityField(name=field["name"], value="".join(map(decode_atom, field["atoms"]))) for field in shown["fields"]
    )
    return Entity(name=name, fields=fields)
