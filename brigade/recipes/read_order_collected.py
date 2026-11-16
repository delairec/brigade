import json

from brigade.recipes.run_order import FIRST_STEP, STEPS_DIRECTORY, OrderRun

COLLECT_KIND = "collect"
SKIPPED_KEY = "skipped"


def read_order_collected(run: OrderRun) -> list[dict]:
    results = [
        json.loads((run.run_directory / STEPS_DIRECTORY / f"{rank}-{COLLECT_KIND}.json").read_text(encoding="utf-8"))
        for rank, step in enumerate(run.recipe["steps"], start=FIRST_STEP)
        if step["kind"] == COLLECT_KIND
    ]
    return [result for result in results if SKIPPED_KEY not in result]
