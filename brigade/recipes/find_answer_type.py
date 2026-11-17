from brigade.errors import BrigadeError
from brigade.recipes.run_order import FIRST_STEP, STEPS_DIRECTORY, OrderRun

JUDGE_KIND = "judge"


def find_answer_type(run: OrderRun) -> str:
    for rank, step in enumerate(run.recipe["steps"], start=FIRST_STEP):
        if (
            step["kind"] == JUDGE_KIND
            and not (run.run_directory / STEPS_DIRECTORY / f"{rank}-{JUDGE_KIND}.json").is_file()
        ):
            return step["answer"]
    raise BrigadeError(f"the run {run.run_id} waits for no judge step")
