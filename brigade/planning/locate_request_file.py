from brigade.planning.mark_request_planned import ENTITY_TYPE as REQUEST_TYPE
from brigade.planning.read_entity_sites import read_entity_sites
from brigade.runtime import Runtime


def locate_request_file(runtime: Runtime, name: str) -> str:
    sites = read_entity_sites(runtime.run_process, runtime.paths.config_root)
    return next(site.file for site in sites if (site.type, site.name) == (REQUEST_TYPE, name))
