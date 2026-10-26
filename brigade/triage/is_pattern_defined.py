from brigade.corpus.read_entities import read_entities
from brigade.runtime import Runtime
from brigade.triage.read_new_pattern import PATTERN_TYPE


def is_pattern_defined(runtime: Runtime, name: str) -> bool:
    if not runtime.paths.schema_file.exists():
        return False
    patterns = read_entities(runtime.run_process, runtime.paths.config_root, PATTERN_TYPE)
    return any(pattern.name == name for pattern in patterns)
