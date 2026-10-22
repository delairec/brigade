from brigade.ledger.append_event import append_event
from brigade.ledger.order_started import OrderStarted
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.study_run_context import STUDY_KIND, STUDY_RECORD_FILE
from brigade.system.write_json_atomically import write_json_atomically

STUDY_RECORD_SCHEMA_VERSION = 1


def start_study_run(runtime: Runtime, study: Study, run_id: str) -> None:
    write_json_atomically(
        runtime.paths.state_root / RUNS_DIRECTORY / run_id / STUDY_RECORD_FILE,
        {
            "schema_version": STUDY_RECORD_SCHEMA_VERSION,
            "study": study.name,
            "project": study.project,
            "wave": study.wave,
        },
    )
    append_event(
        runtime.paths, runtime.now, OrderStarted(project=study.project, kind=STUDY_KIND, order=study.name, run=run_id)
    )
