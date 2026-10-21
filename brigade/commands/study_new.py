import argparse
from functools import partial

from brigade.command import Argument, Command
from brigade.commands.study_run import study_run
from brigade.corpus.check_type_declared import check_type_declared
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.studies.read_collector_line import read_collector_line
from brigade.studies.read_schedule import read_schedule
from brigade.studies.record_study import NewStudy, record_study
from brigade.studies.refuse_inbox_output import refuse_inbox_output
from brigade.studies.require_answer_type import require_answer_type

DOCUMENT_SCHEMA_VERSION = 1

SLOTS = ("report", "explore", "triage", "rules", "none")
DEFAULT_SLOT = "report"
DEFAULT_ANSWER_TYPE = "ANSWER"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    if document["every"] is None:
        return f"@STUDY.{document['study']} recorded, run {document['run']} {document['state']}"
    return f"@STUDY.{document['study']} recorded, every {document['every']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def study_new(request, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    if request.project is not None:
        find_project(read_projects(runtime), request.project)
    for line in request.collector:
        read_collector_line(line)
    require_answer_type(partial(check_type_declared, runtime.run_process), runtime.paths.config_root, request.answer)
    refuse_inbox_output(request.output)
    if request.every is not None:
        read_schedule(request.every)
    record_study(
        runtime,
        NewStudy(
            name=request.name,
            title=request.title,
            question=request.question,
            project=request.project,
            collectors=tuple(request.collector),
            slot=request.slot,
            every=request.every,
            output=request.output,
            answer_type=request.answer,
        ),
    )
    document = {"schema_version": DOCUMENT_SCHEMA_VERSION, "study": request.name, "every": request.every}
    if request.every is not None:
        return document
    ran = study_run(argparse.Namespace(name=request.name, run_id=None), runtime)
    return {**document, "run": ran["run"], "state": ran["state"]}


COMMAND = Command(
    path=("study", "new"),
    help="record a study and run it once unless it has a schedule",
    group_help="record the studies, run them, print their context and take their answers",
    arguments=(
        Argument(("name",), {"help": "the name of the STUDY entity"}),
        Argument(("--title",), {"required": True, "help": "what the study is about"}),
        Argument(("--question",), {"help": "the user's words, verbatim; absent for a scan"}),
        Argument(("--project",), {"help": "the registered project; absent for a machine-wide study"}),
        Argument(
            ("--collector",),
            {
                "action": "append",
                "required": True,
                "help": "a collector and its parameters, or shell: <command>, one argv run without a shell",
            },
        ),
        Argument(("--slot",), {"choices": SLOTS, "default": DEFAULT_SLOT, "help": "the judging slot; none, a scan"}),
        Argument(("--every",), {"help": "a schedule of the tick; absent, the study runs on demand"}),
        Argument(
            ("--output",),
            {"required": True, "help": "file:<path>, entity:<TYPE>, issue or a name; inbox refused until task B22"},
        ),
        Argument(("--answer",), {"default": DEFAULT_ANSWER_TYPE, "help": "the entity type of the answer"}),
    ),
    run=study_new,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
