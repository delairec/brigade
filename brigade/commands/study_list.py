from brigade.command import Command
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.studies.describe_last_study_order import describe_last_study_order
from brigade.studies.read_last_study_orders import read_last_study_orders
from brigade.studies.read_studies import read_studies
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
NO_STUDY = "no study recorded"
NO_VALUE = "-"
COLUMNS = {"name": "name", "status": "status", "every": "every", "last run": "last_run", "outcome": "outcome"}


def _present(value: str | None) -> str:
    return NO_VALUE if value is None else value


def _render_text(document: dict) -> str:
    studies = document["studies"]
    if not studies:
        return NO_STUDY
    return render_table(tuple(COLUMNS), [tuple(_present(study[key]) for key in COLUMNS.values()) for study in studies])


def study_list(request, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    last_orders = read_last_study_orders(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "studies": [
            {
                "name": study.name,
                "status": study.status,
                "every": study.every,
                **describe_last_study_order(last_orders.get(study.name)),
            }
            for study in read_studies(runtime)
        ],
    }


COMMAND = Command(
    path=("study", "list"),
    help="list every study with its schedule, its last run and its outcome",
    run=study_list,
    render_text=_render_text,
)
