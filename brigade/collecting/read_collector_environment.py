import json
from datetime import date
from pathlib import Path

from brigade.collecting.collector_environment import (
    PARAMETERS_VARIABLE,
    PROJECT_PATH_VARIABLE,
    SINCE_VARIABLE,
    CollectorInputs,
)


def read_collector_environment(environment: dict) -> CollectorInputs:
    return CollectorInputs(
        project=Path(environment[PROJECT_PATH_VARIABLE]),
        since=date.fromisoformat(environment[SINCE_VARIABLE]),
        parameters=json.loads(environment[PARAMETERS_VARIABLE]),
    )
