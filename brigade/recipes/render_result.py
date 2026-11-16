import json

from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.recipes.run_order import FIRST_STEP, STEPS_DIRECTORY, OrderRun

RESULT_TYPE = "RESULT"
COLLECT_KIND = "collect"
SKIPPED_KEY = "skipped"
RUN_ID_SEPARATOR = "-"
NAME_SEPARATOR = "_"


def _read_collected(run: OrderRun) -> list[dict]:
    results = [
        json.loads((run.run_directory / STEPS_DIRECTORY / f"{rank}-{COLLECT_KIND}.json").read_text(encoding="utf-8"))
        for rank, step in enumerate(run.recipe["steps"], start=FIRST_STEP)
        if step["kind"] == COLLECT_KIND
    ]
    return [result for result in results if SKIPPED_KEY not in result]


def render_result(run: OrderRun) -> str:
    name = f"{run.order}{NAME_SEPARATOR}{run.run_id.replace(RUN_ID_SEPARATOR, NAME_SEPARATOR)}"
    lines = [
        f"{RESULT_TYPE} {name}",
        f"\tORDER {quote_awawa_string(run.order)}",
        f"\tRUN {quote_awawa_string(run.run_id)}",
    ]
    for collected in _read_collected(run):
        lines.append(f"\tCOLLECTED {quote_awawa_string(collected['collector'])}")
        lines.append(f"\t\tSUMMARY {quote_awawa_string(json.dumps(collected['summary']))}")
        lines.append(f"\t\tDOCUMENT {quote_awawa_string(collected['document'])}")
    return "\n".join(lines) + "\n"
