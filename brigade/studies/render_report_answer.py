import json
from pathlib import Path

from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.read_pattern_origins import read_pattern_origins
from brigade.studies.render_wave_report import WaveEvidence, render_wave_report

CORPUS_FIELD = "CORPUS"


def _read_items(collected: list[dict], collector: str) -> list:
    entry = next(entry for entry in collected if entry["collector"] == collector)
    return json.loads(Path(entry["document"]).read_text(encoding="utf-8"))["items"]


def render_report_answer(runtime: Runtime, study: Study, run_id: str, collected: list[dict]) -> str:
    project = find_project(read_projects(runtime), study.project)
    return render_wave_report(
        WaveEvidence(
            wave=study.wave,
            project=study.project,
            corpus_folder=read_project_field(project, CORPUS_FIELD),
            events=_read_items(collected, "ledger"),
            pull_requests=_read_items(collected, "pr-list"),
            tasks=_read_items(collected, "corpus"),
            changes=_read_items(collected, "git-diff-stat"),
            origins=read_pattern_origins(runtime, study.project),
        )
    )
