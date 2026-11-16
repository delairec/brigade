from brigade.preflights.run_preflight import PreflightPlugins
from brigade.runtime import Runtime
from brigade.system.check_places import locate_checks
from brigade.system.collector_places import locate_collectors
from brigade.system.resolve_plugin import CHECK_KIND, COLLECTOR_KIND


def equip_preflight(runtime: Runtime) -> PreflightPlugins:
    return PreflightPlugins(
        resolve_collector=lambda name, project: runtime.resolve_plugin(
            COLLECTOR_KIND, name, places=locate_collectors(project, runtime.paths)
        ),
        resolve_check=lambda name, project: runtime.resolve_plugin(
            CHECK_KIND, name, places=locate_checks(project, runtime.paths)
        ),
    )
