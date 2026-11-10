import json

from brigade.corpus.read_entity import Entity
from brigade.system.digest_text import digest_text


def digest_task_entity(entity: Entity) -> str:
    return digest_text(json.dumps([[field.name, field.value] for field in entity.fields]))
