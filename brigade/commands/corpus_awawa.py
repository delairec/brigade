from dataclasses import dataclass

from brigade.command import Command
from brigade.corpus.prepare_project_tree import prepare_project_tree
from brigade.corpus.run_awawa import run_awawa
from brigade.runtime import Runtime
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.run_process import ProcessRecord


@dataclass(frozen=True)
class AwawaPassage:
    project: str
    sha: str
    record: ProcessRecord


def _read_request(options):
    return options


def _render_text(passage: AwawaPassage) -> str:
    return passage.record.stdout


def _render_passed_stderr(passage: AwawaPassage) -> str:
    return passage.record.stderr


def _decide_exit_code(passage: AwawaPassage) -> int:
    return passage.record.exit_code


def _describe_diagnostics(passage: AwawaPassage) -> list[str]:
    return [f"@PROJECT.{passage.project} at {passage.sha}"]


def corpus_awawa(request, runtime: Runtime) -> AwawaPassage:
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    tree = prepare_project_tree(request, configuration, runtime)
    record = run_awawa(runtime.run_process, tree.root, request.passed_arguments)
    return AwawaPassage(project=tree.project, sha=tree.sha, record=record)


COMMAND = Command(
    path=("corpus",),
    help="-- <awawa args>: run awawa in a registered project's tree and pass its stdout, stderr and exit code through",
    run=corpus_awawa,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    describe_diagnostics=_describe_diagnostics,
    render_passed_stderr=_render_passed_stderr,
)
