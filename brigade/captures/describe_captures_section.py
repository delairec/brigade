SECTION_HEADING = "## Captures\n\n"
TABLE_HEADING = "\n| Page | Delivered | Reference |\n|---|---|---|\n"
HOSTED = "The repository is public: the images are public too, in a gist of the machine account."
NOT_HOSTED = (
    "Nothing is hosted: the repository is private, or its visibility could not be read. The captures stay in the"
    " state directory of the machine that ran brigade, where the review reads them."
)


def _describe_hosted(page: dict, urls: dict[str, str]) -> str:
    name = page["page"]
    return (
        f"| {name} | ![{name} delivered]({urls[page['delivered']]})"
        f" | ![{name} reference]({urls[page['reference']]}) |\n"
    )


def _describe_local(page: dict) -> str:
    return f"| {page['page']} | `{page['delivered']}` | `{page['reference']}` |\n"


def describe_captures_section(pages: list[dict], head: str, urls: dict[str, str] | None) -> str:
    opening = f"{SECTION_HEADING}Each page the task covers at {head}, delivered beside its reference. "
    if urls is None:
        return f"{opening}{NOT_HOSTED}\n{TABLE_HEADING}" + "".join(_describe_local(page) for page in pages)
    return f"{opening}{HOSTED}\n{TABLE_HEADING}" + "".join(_describe_hosted(page, urls) for page in pages)
