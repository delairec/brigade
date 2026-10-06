from typing import Optional

from brigade.corpus.read_entities import read_entities

POLICY_TYPE = "POLICY"
HANDOVERS_BY_DEFAULT = 2


def read_handovers(runtime, project: Optional[str]) -> int:
    if project is None:
        return HANDOVERS_BY_DEFAULT
    reference = f"@PROJECT.{project}"
    for policy in read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE):
        values = {field.name: field.value for field in policy.fields}
        if values.get("PROJECT") == reference:
            return int(values.get("HANDOVERS", HANDOVERS_BY_DEFAULT))
    return HANDOVERS_BY_DEFAULT
