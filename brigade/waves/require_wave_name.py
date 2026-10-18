from brigade.errors import BrigadeError
from brigade.waves.find_wave_name import find_wave_name


def require_wave_name(events: tuple, request: dict) -> str:
    wave = find_wave_name(events, request["project"], request["branch"])
    if wave is None:
        raise BrigadeError(
            f"no wave.started of @PROJECT.{request['project']} names {request['branch']},"
            f" the BRANCH of @REQUEST.{request['name']}"
        )
    return wave
