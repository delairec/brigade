import math
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Optional

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError, UsageError
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.roles.resolve_role import NO_PROJECT_BINDINGS, ResolvedRole, RoleBindings, resolve_role
from brigade.runs.create_run_id import create_run_id
from brigade.runs.read_handovers import read_handovers
from brigade.runs.resolve_procedure import Procedure, ProcedureDirectories, resolve_procedure
from brigade.runs.run_locations import DISPOSABLE_WORKTREE_DIRECTORY, RUNS_DIRECTORY
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_named_client import ask_named_client
from brigade.system.read_configuration import Configuration, read_configuration

CONFIGURATION_FILE = "config.toml"
PROBE_REQUEST = {"schema_version": 1}
SHIPPED_PROCEDURES = files("brigade.runs") / "data" / "procedures"
STEP_COUNT_FEATURE = "step_count"
TOOL_GRANTS_FEATURE = "tool_grants"
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
    project: Optional[str]
    cwd: Optional[str]
    brief: Optional[str]
    arguments: tuple[str, ...]
    run_id: Optional[str]


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    run_directory: Path
    procedure: Procedure
    slot: str
    role: ResolvedRole
    client: str
    configuration: Configuration
    project: Optional[str]
    cwd: Path
    worktree: Path
    disposable_worktree: bool
    capabilities: tuple[str, ...]
    wall_limit_s: float
    arguments: dict
    brief_path: Optional[Path]
    brief: Optional[str]
    counts_steps: bool
    handovers: int
    warnings: tuple[str, ...]


def _read_values(project: Optional[Entity], field_name: str) -> list[str]:
    if project is None:
        return []
    return [field.value for field in project.fields if field.name == field_name]


def _read_value(project: Optional[Entity], field_name: str) -> Optional[str]:
    return next(iter(_read_values(project, field_name)), None)


def _read_project(name: Optional[str], runtime) -> Optional[Entity]:
    if name is None:
        return None
    require_operational_corpus(runtime.paths.config_root)
    return find_project(read_projects(runtime), name)


def _read_role_binding(project: Entity, value: str) -> tuple[str, str]:
    slot, separator, name = value.partition(BINDING_SEPARATOR)
    if not separator or not slot.strip() or not name.strip():
        raise BrigadeError(f"@PROJECT.{project.name} has ROLE {value}, not slot=name")
    return slot.strip(), name.strip()


def _read_bindings(project: Optional[Entity]) -> RoleBindings:
    if project is None:
        return NO_PROJECT_BINDINGS
    path = _read_value(project, "PATH")
    return RoleBindings(
        project=project.name,
        roles=dict(_read_role_binding(project, value) for value in _read_values(project, "ROLE")),
        roleset=_read_value(project, "ROLESET"),
        project_path=None if path is None else Path(path),
    )


def _locate_cwd(cwd: Optional[str], project: Optional[Entity]) -> Path:
    project_path = _read_value(project, "PATH")
    if cwd is not None:
        directory = Path(cwd).absolute()
    elif project_path is not None:
        directory = Path(project_path)
    else:
        directory = Path.cwd()
    if not directory.is_dir():
        raise BrigadeError(f"no directory {directory}")
    return directory


def _read_brief(brief: Optional[str]) -> tuple[Optional[Path], Optional[str]]:
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


def _choose_run_id(run_id: Optional[str], runtime) -> str:
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


def plan_run(request: RunRequest, runtime) -> RunPlan:
    configuration_path = runtime.paths.config_root / CONFIGURATION_FILE
    configuration = read_configuration(configuration_path)
    project = _read_project(request.project, runtime)
    client = _read_value(project, "CLIENT") or configuration.client
    if client is None:
        raise BrigadeError(f"config.toml names no client: set the client key in {configuration_path}")
    directories = ProcedureDirectories(shipped=SHIPPED_PROCEDURES, instructions=configuration.instructions)
    procedure = resolve_procedure(request.procedure, directories)
    role = resolve_role(request.slot, runtime, _read_bindings(project))
    role_capabilities = _read_role_capabilities(role)
    capabilities = tuple(capability for capability in procedure.capabilities if capability in role_capabilities)
    features = ask_named_client(runtime, configuration, ClientQuestion(client, "probe", PROBE_REQUEST))["features"]
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
        configuration=configuration,
        project=request.project,
        cwd=cwd,
        worktree=run_directory / DISPOSABLE_WORKTREE_DIRECTORY if disposable_worktree else cwd,
        disposable_worktree=disposable_worktree,
        capabilities=capabilities,
        wall_limit_s=wall_limit_s,
        arguments=arguments,
        brief_path=brief_path,
        brief=brief,
        counts_steps=counts_steps,
        handovers=read_handovers(runtime, request.project),
        warnings=warnings,
    )
