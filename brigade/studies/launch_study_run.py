from brigade.runs.create_run_id import create_run_id
from brigade.runs.record_run_pid import record_run_pid
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.detach_study_run import detach_study_run
from brigade.studies.start_study_run import start_study_run


def launch_study_run(runtime: Runtime, study: Study) -> str:
    run_id = create_run_id(runtime.now)
    start_study_run(runtime, study, run_id)
    detach_study_run(runtime, study.name, run_id, record_run_pid)
    return run_id
