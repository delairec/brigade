from brigade.dashboard.route_command import OPTION_PREFIX, PATH_SEPARATOR, PROJECT_LISTING, WAVE_LISTING, CommandRoute

PROJECT_ACTIONS = ("pause", "resume")
WAVE_RESUME = "resume"
TASKS_SEGMENT = "tasks"
TASK_REQUEUE = "requeue"


def _is_named(segment: str) -> bool:
    return bool(segment) and not segment.startswith(OPTION_PREFIX)


def _route_project_action(project: str, action: str) -> CommandRoute | None:
    if action not in PROJECT_ACTIONS:
        return None
    return CommandRoute(arguments=("project", action, "--json", project), identifier=project, listing=PROJECT_LISTING)


def _route_wave_action(wave: str, rest: list[str]) -> CommandRoute | None:
    if rest == [WAVE_RESUME]:
        return CommandRoute(arguments=("wave", "resume", "--json", wave), identifier=wave, listing=WAVE_LISTING)
    if len(rest) == 3 and rest[0] == TASKS_SEGMENT and rest[2] == TASK_REQUEUE and _is_named(rest[1]):
        return CommandRoute(
            arguments=("wave", "requeue", "--json", wave, rest[1]), identifier=wave, listing=WAVE_LISTING
        )
    return None


def route_action(target: str) -> CommandRoute | None:
    segments = target.split(PATH_SEPARATOR)
    if len(segments) < 3 or not _is_named(segments[1]):
        return None
    collection, identifier, *rest = segments
    if collection == "projects" and len(rest) == 1:
        return _route_project_action(identifier, rest[0])
    if collection == "waves":
        return _route_wave_action(identifier, rest)
    return None
