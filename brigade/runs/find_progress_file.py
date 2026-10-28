from pathlib import Path

from brigade.runs.run_locations import PROGRESS_STEM
from brigade.system.name_document_plugin import DOCUMENT_PLUGINS_BY_EXTENSION


def find_progress_file(run_directory: Path) -> Path | None:
    candidates = (run_directory / f"{PROGRESS_STEM}{extension}" for extension in DOCUMENT_PLUGINS_BY_EXTENSION)
    return next((candidate for candidate in candidates if candidate.is_file()), None)
