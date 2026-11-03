from collections.abc import Callable

from brigade.mining.read_text_scrubber import read_text_scrubber
from brigade.runtime import Runtime


def _scrub(value, scrub_text: Callable[[str], str]):
    if isinstance(value, dict):
        return {key: _scrub(item, scrub_text) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item, scrub_text) for item in value]
    if not isinstance(value, str):
        return value
    return scrub_text(value)


def scrub_document(document: dict, runtime: Runtime) -> dict:
    return _scrub(document, read_text_scrubber(runtime.run_process, runtime.paths.config_root))
