import json

from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.studies.read_study import Study

RUN_ID_SEPARATOR = "-"
NAME_SEPARATOR = "_"


def name_answer(study: Study, run_id: str) -> str:
    return f"{study.name}{NAME_SEPARATOR}{run_id.replace(RUN_ID_SEPARATOR, NAME_SEPARATOR)}"


def render_answer(study: Study, run_id: str, collected: list[dict]) -> str:
    lines = [
        f"{study.answer_type} {name_answer(study, run_id)}",
        f"\tSTUDY {quote_awawa_string(study.name)}",
        f"\tRUN {quote_awawa_string(run_id)}",
    ]
    for entry in collected:
        lines.append(f"\tCOLLECTED {quote_awawa_string(entry['collector'])}")
        lines.append(f"\t\tSUMMARY {quote_awawa_string(json.dumps(entry['summary']))}")
        lines.append(f"\t\tDOCUMENT {quote_awawa_string(entry['document'])}")
    return "\n".join(lines) + "\n"
