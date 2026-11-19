import argparse
import json
import sys

from brigade.command import Command
from brigade.corpus.corpus_view_answerer import CorpusViewAnswerer
from brigade.corpus.read_awawa_version import read_awawa_version
from brigade.dashboard.answer_addon_lines import answer_addon_lines
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1


def awawa_addon(request: argparse.Namespace, runtime: Runtime) -> dict:
    version = read_awawa_version(runtime.run_process)
    require_operational_corpus(runtime.paths)
    answerer = CorpusViewAnswerer(read_projects(runtime), runtime, runtime.run_process)
    sys.stdout.write(f"{json.dumps({'awawa': version})}\n")
    sys.stdout.flush()
    answered = answer_addon_lines(request.standard_input, sys.stdout, answerer.answer)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "answered": answered}


def _render_text(document: dict) -> str:
    return f"answered {document['answered']} requests of the awawa tab"


COMMAND = Command(
    path=("awawa-addon",),
    help="answer the documents of the awawa tab over standard input and output, one JSON line each;"
    " brigade serve starts it",
    arguments=(),
    run=awawa_addon,
    render_text=_render_text,
)
