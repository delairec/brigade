from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.waves.list_candidate_waves import list_candidate_waves
from brigade.waves.read_project_tasks import ProjectTasksReading, read_project_tasks
from brigade.waves.start_project_wave import WaveStart, start_project_wave

MILESTONE_FIELD = "MILESTONE"
MILESTONE_PREFIX = "@MILESTONE."
NO_MILESTONE = None


def _describe_milestone(milestone: str | None) -> str:
    return "no milestone" if milestone is None else milestone


def _read_named_milestone(runtime: Runtime, start: WaveStart, reading: ProjectTasksReading) -> str | None:
    main = read_project_tasks(runtime, reading, NO_MILESTONE)
    defined = [task for task in start.tasks if task in main.by_name]
    named = {task: read_project_field(main.by_name[task], MILESTONE_FIELD) for task in defined}
    milestones = set(named.values())
    if len(milestones) > 1:
        naming = ", ".join(f"@TASK.{task} names {_describe_milestone(milestone)}" for task, milestone in named.items())
        raise BrigadeError(f"{naming}: a wave takes the tasks of one milestone or tasks naming none")
    [milestone] = milestones or {NO_MILESTONE}
    return None if milestone is None else milestone.removeprefix(MILESTONE_PREFIX)


def start_project_waves(runtime: Runtime, start: WaveStart) -> tuple[dict, ...]:
    require_operational_corpus(runtime.paths)
    reading = ProjectTasksReading(
        configuration=start.configuration,
        project=find_project(read_projects(runtime), start.project),
        read_environment=start.read_environment,
        entries=read_ledger(runtime.paths.state_root).entries,
    )
    if start.tasks:
        return (start_project_wave(runtime, start, _read_named_milestone(runtime, start, reading)),)
    waves = list_candidate_waves(runtime, reading)
    if not waves:
        raise BrigadeError(f"@PROJECT.{start.project} has no task to start")
    return tuple(start_project_wave(runtime, start, wave.milestone) for wave in waves)
