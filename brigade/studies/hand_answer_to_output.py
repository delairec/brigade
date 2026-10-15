import json
import shutil

from brigade.errors import BrigadeError
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.run_process import ProcessRequest

OUTPUT_EXECUTABLE_PREFIX = "brigade-output-"
OUTPUT_TIMEOUT_S = 120.0
OUTPUT_REQUEST_SCHEMA_VERSION = 1


def hand_answer_to_output(context: StudyRunContext, publication: AnswerPublication) -> dict:
    name = context.study.output
    executable_name = f"{OUTPUT_EXECUTABLE_PREFIX}{name}"
    executable = shutil.which(executable_name, path=context.runtime.paths.executable_search_path)
    if executable is None:
        raise BrigadeError(f"no output {name}: no {executable_name} on PATH")
    request = {
        "schema_version": OUTPUT_REQUEST_SCHEMA_VERSION,
        "study": context.study.name,
        "run": context.run_id,
        "markdown": publication.markdown,
    }
    context.runtime.run_process(
        ProcessRequest(
            argv=(executable,), cwd=str(context.run_directory), timeout_s=OUTPUT_TIMEOUT_S, stdin=json.dumps(request)
        )
    )
    return {"executable": executable}
