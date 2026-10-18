import math
import re
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError, UsageError
from brigade.registry.read_project_field import read_project_field
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, ResolvedRole, RoleBindings, resolve_role
from brigade.runs.create_run_id import create_run_id
from brigade.runs.read_handovers import read_handovers
from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_setting import RunSetting
from brigade.runs.resolve_procedure import Procedure, ProcedureDirectories, resolve_procedure
from brigade.runs.run_locations import (
    DISPOSABLE_WORKTREE_DIRECTORY,
    PROGRESS_STEM,
    RESULT_FILE,
    RUNS_DIRECTORY,
    SEGMENTS_DIRECTORY,
)
from brigade.runtime import Runtime
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.name_document_plugin import EXTENSIONS_BY_DOCUMENT_PLUGIN
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_configuration import Configuration

SHIPPED_PROCEDURES = files("brigade.runs") / "data" / "procedures"
STEP_COUNT_FEATURE = "step_count"
TOOL_GRANTS_FEATURE = "tool_grants"
ACTIONS_OPERATION = "actions"
TRANSCRIPTS_OPERATION = "transcripts"
RESUME_OPERATION = "resume"
FIRST_SEGMENT = 1
SEGMENT_RESULT_SHAPE = {}
WRITE_CAPABILITY = "write"
CAPABILITY_SEPARATOR = ","
BINDING_SEPARATOR = "="
ARGUMENT_SEPARATOR = "="
CAP_MARGIN = 1.25
RUN_ID_PATTERN = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{6}")


@dataclass(frozen=True)
class RunRequest:
    procedure: str
    slot: str
    project: str | None
    cwd: str | None
    brief: str | None
    arguments: tuple[str, ...]
    run_id: str | None
    wave: str | None
    task: str | None
    resume: bool = False


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    run_directory: Path
    procedure: Procedure
    slot: str
    role: ResolvedRole
    client: str
    client_adapter: object
    document: object
    progress_file: Path
    configuration: Configuration
    project: str | None
    cwd: Path
    worktree: Path
    disposable_worktree: bool
    capabilities: tuple[str, ...]
    wall_limit_s: float
    arguments: dict
    wave: str | None
    task: str | None
    brief_path: Path | None
    brief: str | None
    counts_steps: bool
    reads_actions: bool
    reads_transcripts: bool
    handovers: int
    warnings: tuple[str, ...]
    resumed: bool = False
    first_segment: int = FIRST_SEGMENT
    resumed_session: str | None = None
    forge_environment: dict = field(default_factory=dict, repr=False)


def _read_values(project: Entity, field_name: str) -> list[str]:
    return [field.value for field in project.fields if field.name == field_name]


def _read_role_binding(project: Entity, value: str) -> tuple[str, str]:
    slot, separator, name = value.partition(BINDING_SEPARATOR)
    if not separator or not slot.strip() or not name.strip():
        raise BrigadeError(f"@PROJECT.{project.name} has ROLE {value}, not slot=name")
    return slot.strip(), name.strip()


def _read_bindings(project: Entity | None) -> RoleBindings:
    if project is None:
        return NO_PROJECT_BINDINGS
    path = read_project_field(project, "PATH")
    return RoleBindings(
        project=project.name,
        roles=dict(_read_role_binding(project, value) for value in _read_values(project, "ROLE")),
        roleset=read_project_field(project, "ROLESET"),
        project_path=None if path is None else Path(path),
    )


def _locate_cwd(cwd: str | None, project: Entity | None) -> Path:
    project_path = read_project_field(project, "PATH")
    if cwd is not None:
        directory = Path(cwd).absolute()
    elif project_path is not None:
        directory = Path(project_path)
    else:
        directory = Path.cwd()
    if not directory.is_dir():
        raise BrigadeError(f"no directory {directory}")
    return directory


def _read_brief(brief: str | None) -> tuple[Path | None, str | None]:
    if brief is None:
        return None, None
    path = Path(brief).absolute()
    if not path.is_file():
        raise BrigadeError(f"no brief file {path}")
    return path, path.read_text(encoding="utf-8")


def _read_argument(argument: str) -> tuple[str, str]:
    key, separator, value = argument.partition(ARGUMENT_SEPARATOR)
    if not separator or not key:
        raise BrigadeError(f"the argument {argument} is not key=value")
    return key, value


def _choose_run_id(run_id: str | None, runtime: Runtime) -> str:
    if run_id is None:
        return create_run_id(runtime.now)
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise UsageError(f"{run_id} is not a run id")
    return run_id


def _read_role_capabilities(role: ResolvedRole) -> set[str]:
    return {capability.strip() for capability in role.front_matter["capabilities"].split(CAPABILITY_SEPARATOR)}


def _describe_clock_warning(client: str, budget: int, wall_limit_s: float) -> str:
    return (
        f"{client} counts no steps: the budget of {budget} steps is held on the clock"
        f" and the run cut at its limit of {wall_limit_s:g} s"
    )


def _count_segments(run_directory: Path) -> int:
    return sum(1 for segment in (run_directory / SEGMENTS_DIRECTORY).iterdir() if segment.is_dir())


def _read_session(run_directory: Path, segment: int) -> str | None:
    path = run_directory / SEGMENTS_DIRECTORY / str(segment) / RESULT_FILE
    return read_run_document(path, "segment result", SEGMENT_RESULT_SHAPE)["session"]


def plan_run(request: RunRequest, setting: RunSetting, client_adapter, document, runtime: Runtime) -> RunPlan:
    configuration = setting.configuration
    project = setting.project
    client = setting.client
    directories = ProcedureDirectories(shipped=SHIPPED_PROCEDURES, instructions=configuration.instructions)
    procedure = resolve_procedure(request.procedure, directories)
    role = resolve_role(request.slot, runtime, _read_bindings(project), configuration)
    role_capabilities = _read_role_capabilities(role)
    capabilities = tuple(capability for capability in procedure.capabilities if capability in role_capabilities)
    probe = ask_named_client(client_adapter, ClientQuestion(client, ProbeRequest()), configuration, runtime)
    features = probe.features
    counts_steps = STEP_COUNT_FEATURE in features
    cwd = _locate_cwd(request.cwd, project)
    brief_path, brief = _read_brief(request.brief)
    arguments = dict(_read_argument(argument) for argument in request.arguments)
    run_id = _choose_run_id(request.run_id, runtime)
    run_directory = runtime.paths.state_root / RUNS_DIRECTORY / run_id
    disposable_worktree = TOOL_GRANTS_FEATURE not in features and WRITE_CAPABILITY not in capabilities
    wall_limit_s = math.ceil(procedure.budget * CAP_MARGIN) * configuration.seconds_per_step
    warnings = () if counts_steps else (_describe_clock_warning(client, procedure.budget, wall_limit_s),)
    return RunPlan(
        run_id=run_id,
        run_directory=run_directory,
        procedure=procedure,
        slot=request.slot,
        role=role,
        client=client,
        client_adapter=client_adapter,
        document=document,
        progress_file=run_directory / f"{PROGRESS_STEM}{EXTENSIONS_BY_DOCUMENT_PLUGIN[configuration.document]}",
        configuration=configuration,
        project=request.project,
        cwd=cwd,
        worktree=run_directory / DISPOSABLE_WORKTREE_DIRECTORY if disposable_worktree else cwd,
        disposable_worktree=disposable_worktree,
        capabilities=capabilities,
        wall_limit_s=wall_limit_s,
        arguments=arguments,
        wave=request.wave,
        task=request.task,
        brief_path=brief_path,
        brief=brief,
        counts_steps=counts_steps,
        reads_actions=ACTIONS_OPERATION in probe.operations,
        reads_transcripts=TRANSCRIPTS_OPERATION in probe.operations,
        handovers=read_handovers(runtime, request.project),
        resumed=request.resume,
        first_segment=_count_segments(run_directory) + 1 if request.resume else FIRST_SEGMENT,
        resumed_session=(
            _read_session(run_directory, _count_segments(run_directory))
            if request.resume and RESUME_OPERATION in probe.operations
            else None
        ),
        warnings=warnings,
    )
