from collections.abc import Callable
from pathlib import Path

from brigade.recipes.render_result import render_result
from brigade.recipes.run_order import OrderRun, StepPerformer
from brigade.studies.study_run_context import ANSWER_FILE
from brigade.system.write_text_atomically import write_text_atomically


def _read_answer(run: OrderRun) -> str:
    answer_path = run.run_directory / ANSWER_FILE
    if not answer_path.is_file():
        write_text_atomically(answer_path, render_result(run))
    return answer_path.read_text(encoding="utf-8")


def create_output_performer(
    keep: Callable[[str], None], hand: Callable[[str, Path], dict], output: str | None
) -> StepPerformer:
    def perform(step: dict, run: OrderRun) -> dict:
        keep(_read_answer(run))
        target = output or step["output"]
        answer_path = run.run_directory / ANSWER_FILE
        return {"output": target, "answer": str(answer_path), **hand(target, answer_path)}

    return perform
