import shutil

from brigade.errors import BrigadeError
from brigade.studies.choose_answer_publisher import PUBLISHERS_BY_OUTPUT
from brigade.studies.hand_answer_to_output import OUTPUT_EXECUTABLE_PREFIX
from brigade.studies.write_answer import ENTITY_OUTPUT_PREFIX
from brigade.studies.write_answer_to_file import FILE_OUTPUT_PREFIX


def resolve_output(name: str, executable_search_path: str) -> None:
    if name in PUBLISHERS_BY_OUTPUT or name.startswith((FILE_OUTPUT_PREFIX, ENTITY_OUTPUT_PREFIX)):
        return
    executable_name = f"{OUTPUT_EXECUTABLE_PREFIX}{name}"
    if shutil.which(executable_name, path=executable_search_path) is None:
        raise BrigadeError(f"no output {name}: no {executable_name} on PATH")
