from brigade.runtime import Runtime
from brigade.waves.is_asked_by_policy import ASKING, is_asked_by_policy

ASKING_WAVE_START = ASKING
AUTOMATIC_WAVE_START = "auto"


def read_wave_start(runtime: Runtime, project: str) -> str:
    return ASKING_WAVE_START if is_asked_by_policy(runtime, project, "WAVE_START") else AUTOMATIC_WAVE_START
