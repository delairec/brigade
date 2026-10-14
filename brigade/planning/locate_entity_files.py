from pathlib import PurePosixPath

from brigade.planning.read_entity_sites import EntitySite


def locate_entity_files(sites: tuple[EntitySite, ...], folder: str) -> dict[str, str]:
    files = {}
    for site in sorted(sites, key=lambda site: site.file):
        if PurePosixPath(site.file).is_relative_to(folder):
            files.setdefault(site.type, site.file)
    return files
