from collections.abc import Callable

from brigade.preflights.run_preflight import PreflightPlugins
from brigade.system.check_places import locate_checks
from brigade.system.collector_places import locate_collectors
from brigade.system.paths import Paths
from brigade.system.resolve_check import resolve_check
from brigade.system.resolve_collector import resolve_collector
from brigade.system.resolve_plugin import CHECK_KIND, COLLECTOR_KIND, resolve_plugin

NO_PLUGIN_SOURCES = None


def create_preflight_plugins(paths: Paths) -> PreflightPlugins:
    return PreflightPlugins(
        resolve_collector=lambda name, project: resolve_collector(name, locate_collectors(project, paths)),
        resolve_check=lambda name, project: resolve_check(name, locate_checks(project, paths)),
    )


def resolve_preflight_kinds_or(resolve_other: Callable) -> Callable:
    def resolve(kind: str, name: str, **options):
        if kind in (COLLECTOR_KIND, CHECK_KIND):
            return resolve_plugin(kind, name, NO_PLUGIN_SOURCES, **options)
        return resolve_other(kind, name, **options)

    return resolve
