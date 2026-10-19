import argparse

from brigade.errors import BrigadeError
from brigade.studies.study_run_context import ANSWER_FILE, StudyRunContext

JUDGING_PROCEDURE = "study"
SCAN_SLOT = "none"
NO_JUDGING_RUN = None


def judge_evidence(context: StudyRunContext) -> dict:
    study = context.study
    if study.slot == SCAN_SLOT:
        return {"run": NO_JUDGING_RUN}
    judging = argparse.Namespace(
        procedure=JUDGING_PROCEDURE,
        slot=study.slot,
        project=study.project,
        cwd=None,
        brief=None,
        arguments=(f"study={study.name}", f"run={context.run_id}"),
        run_id=None,
        wave=None,
        task=None,
        detach=False,
        resume=False,
    )
    launched = context.equipment.launch_run(judging, context.runtime)
    if not (context.run_directory / ANSWER_FILE).is_file():
        raise BrigadeError(f"the judging run {launched['run']} gave no answer")
    return {"run": launched["run"]}
