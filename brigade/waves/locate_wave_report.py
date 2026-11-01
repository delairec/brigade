from brigade.corpus.read_entity import Entity
from brigade.registry.read_project_field import read_project_field

CORPUS_FIELD = "CORPUS"
WAVE_NUMBER_SEPARATOR = "_w"


def locate_wave_report(project: Entity, wave: str) -> str:
    wave_number = wave.rsplit(WAVE_NUMBER_SEPARATOR, 1)[1]
    return f"{read_project_field(project, CORPUS_FIELD)}/waves/{wave_number}-report.md"
