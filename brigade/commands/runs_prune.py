from brigade.command import Argument, Command
from brigade.runs.describe_skipped_runs import describe_skipped_runs
from brigade.runs.prune_runs import PruneRequest, prune_runs
from brigade.runtime import Runtime
from brigade.system.read_day import read_day
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.read_positive_count import read_positive_count

DOCUMENT_SCHEMA_VERSION = 1
NO_RUN_REMOVED = "no run removed"


def _name_removal(document: dict) -> str:
    if document["dry_run"]:
        return "would remove"
    return "removed"


def _render_text(document: dict) -> str:
    if not document["runs"]:
        return NO_RUN_REMOVED
    removal = _name_removal(document)
    return "\n".join(f"{removal} {removed['run']} ({removed['state']})" for removed in document["runs"])


def _choose_keep(request, runtime: Runtime) -> int:
    if request.keep is not None:
        return request.keep
    return read_optional_configuration(runtime.paths.configuration_file).runs_kept


def runs_prune(request, runtime: Runtime) -> dict:
    prune = PruneRequest(
        paths=runtime.paths,
        keep=_choose_keep(request, runtime),
        before=request.before,
        resumable=request.resumable,
        dry_run=request.dry_run,
    )
    outcome = prune_runs(prune)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "dry_run": request.dry_run,
        "runs": outcome.removed,
        "skipped": outcome.skipped,
    }


def _describe_diagnostics(document: dict) -> list[str]:
    return describe_skipped_runs(document["skipped"])


COMMAND = Command(
    path=("runs", "prune"),
    help="remove the finished and dead runs beyond the bound, or older than a day; a running run stays",
    group_help="list the runs, show one, stop one and prune them",
    arguments=(
        Argument(
            ("--keep",),
            {"type": read_positive_count, "help": "the runs kept, newest first, in place of runs_kept of config.toml"},
        ),
        Argument(
            ("--before",), {"type": read_day, "help": "remove every run settled before this day YYYY-MM-DD in UTC"}
        ),
        Argument(
            ("--resumable",),
            {"action": "store_true", "help": "remove the runs a resume after a rate limit takes up as well"},
        ),
        Argument(("--dry-run",), {"action": "store_true", "help": "print what would go and remove nothing"}),
    ),
    run=runs_prune,
    render_text=_render_text,
    describe_diagnostics=_describe_diagnostics,
)
