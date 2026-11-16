from brigade.preflights.run_preflight import PreflightPlugins
from brigade.system.check_places import locate_checks
from brigade.system.collector_places import locate_collectors
from brigade.system.paths import Paths
from brigade.system.resolve_check import resolve_check
from brigade.system.resolve_collector import resolve_collector


def create_preflight_plugins(paths: Paths) -> PreflightPlugins:
    return PreflightPlugins(
        resolve_collector=lambda name, project: resolve_collector(name, locate_collectors(project, paths)),
        resolve_check=lambda name, project: resolve_check(name, locate_checks(project, paths)),
    )
