import json
from pathlib import Path

from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.read_pattern_origins import read_pattern_origins
from brigade.studies.render_milestone_report import ReportEvidence, render_milestone_report

CORPUS_FIELD = "CORPUS"
MILESTONE_FIELD = "MILESTONE"
TASK_FIELD = "TASK"


def _read_items(collected: list[dict], collector: str) -> list:
    return [
        item
        for entry in collected
        if entry["collector"] == collector
        for item in json.loads(Path(entry["document"]).read_text(encoding="utf-8"))["items"]
    ]


def _name_subject(study: Study) -> tuple[str, str]:
    if study.task is not None:
        return TASK_FIELD, study.task.task
    return MILESTONE_FIELD, study.milestone.milestone


def render_report_answer(runtime: Runtime, study: Study, run_id: str, collected: list[dict]) -> str:
    project = find_project(read_projects(runtime), study.project)
    subject_field, subject = _name_subject(study)
    return render_milestone_report(
        ReportEvidence(
            subject_field=subject_field,
            subject=subject,
            project=study.project,
            corpus_folder=read_project_field(project, CORPUS_FIELD),
            events=_read_items(collected, "ledger"),
            pull_requests=_read_items(collected, "pr-list"),
            tasks=_read_items(collected, "corpus"),
            changes=_read_items(collected, "git-diff-stat"),
            origins=read_pattern_origins(runtime, study.project),
        )
    )
