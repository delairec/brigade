import json

from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.studies.study_run_context import StudyRunContext

RUN_ID_SEPARATOR = "-"
NAME_SEPARATOR = "_"


def _name_answer(context: StudyRunContext) -> str:
    return f"{context.study.name}{NAME_SEPARATOR}{context.run_id.replace(RUN_ID_SEPARATOR, NAME_SEPARATOR)}"


def render_answer(context: StudyRunContext, collected: list[dict]) -> str:
    lines = [
        f"{context.study.answer_type} {_name_answer(context)}",
        f"\tSTUDY {quote_awawa_string(context.study.name)}",
        f"\tRUN {quote_awawa_string(context.run_id)}",
    ]
    for entry in collected:
        lines.append(f"\tCOLLECTED {quote_awawa_string(entry['collector'])}")
        lines.append(f"\t\tSUMMARY {quote_awawa_string(json.dumps(entry['summary']))}")
        lines.append(f"\t\tDOCUMENT {quote_awawa_string(entry['document'])}")
    return "\n".join(lines) + "\n"
