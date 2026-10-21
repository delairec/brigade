from functools import partial

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.planning.mark_request_planned import ENTITY_TYPE as REQUEST_TYPE
from brigade.planning.read_entity_sites import read_entity_sites
from brigade.runtime import Runtime


def locate_request_file(runtime: Runtime, name: str) -> str:
    sites = read_entity_sites(partial(read_awawa_document, runtime.run_process), runtime.paths.config_root)
    return next(site.file for site in sites if (site.type, site.name) == (REQUEST_TYPE, name))
