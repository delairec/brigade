SECTION_OPENING = (
    "## Captures\n"
    "\n"
    "Each page the task covers, delivered beside its reference. The images are public, in a gist of the"
    " machine account, as for every pull request the tick opens with captures.\n"
    "\n"
    "| Page | Delivered | Reference |\n"
    "|---|---|---|\n"
)


def _describe_page(page: dict, urls: dict[str, str]) -> str:
    name = page["page"]
    return (
        f"| {name} | ![{name} delivered]({urls[page['delivered']]})"
        f" | ![{name} reference]({urls[page['reference']]}) |\n"
    )


def describe_captures_section(pages: list[dict], urls: dict[str, str]) -> str:
    return SECTION_OPENING + "".join(_describe_page(page, urls) for page in pages)
