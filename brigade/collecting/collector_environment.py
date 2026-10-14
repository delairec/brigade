import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_PATH_VARIABLE = "BRIGADE_PROJECT_PATH"
SINCE_VARIABLE = "BRIGADE_SINCE"
PARAMETERS_VARIABLE = "BRIGADE_PARAMS"


@dataclass(frozen=True)
class CollectorInputs:
    project: Path
    since: date
    parameters: dict


def create_collector_environment(inputs: CollectorInputs) -> dict:
    return {
        PROJECT_PATH_VARIABLE: str(inputs.project),
        SINCE_VARIABLE: inputs.since.isoformat(),
        PARAMETERS_VARIABLE: json.dumps(inputs.parameters),
    }
