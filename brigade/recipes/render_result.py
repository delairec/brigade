import json

from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.recipes.name_result import name_result
from brigade.recipes.read_order_collected import read_order_collected
from brigade.recipes.run_order import OrderRun

RESULT_TYPE = "RESULT"


def render_result(run: OrderRun) -> str:
    lines = [
        f"{RESULT_TYPE} {name_result(run)}",
        f"\tORDER {quote_awawa_string(run.order)}",
        f"\tRUN {quote_awawa_string(run.run_id)}",
    ]
    for collected in read_order_collected(run):
        lines.append(f"\tCOLLECTED {quote_awawa_string(collected['collector'])}")
        lines.append(f"\t\tSUMMARY {quote_awawa_string(json.dumps(collected['summary']))}")
        lines.append(f"\t\tCOLLECTION {quote_awawa_string(collected['collection'])}")
    return "\n".join(lines) + "\n"
