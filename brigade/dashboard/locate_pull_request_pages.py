PULL_REQUEST_PAGES_BY_FORGE = {"github": "https://github.com/{remote}/pull/"}
NO_PAGE = None


def locate_pull_request_pages(project_document: dict) -> str | None:
    fields = {field["name"]: field["value"] for field in project_document["project"]["fields"]}
    pages = PULL_REQUEST_PAGES_BY_FORGE.get(fields.get("FORGE"))
    if pages is None or "REMOTE" not in fields:
        return NO_PAGE
    return pages.format(remote=fields["REMOTE"])
