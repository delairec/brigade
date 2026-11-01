from dataclasses import dataclass

ARGUMENT_SEPARATOR = "="
PROGRESS_SECTION = "Progress so far"
END_OF_SEGMENT = (
    "End your final message on one of these lines: brigade-end: done once the work is delivered,"
    " brigade-end: handed_over when a next segment resumes it from the progress file,"
    " brigade-end: blocked when it waits for a ruling."
)


@dataclass(frozen=True)
class BriefParts:
    progress: str | None
    procedure: str
    procedure_body: str
    arguments: dict
    brief: str | None
    progress_description: str
    budget: int


def _render_section(title: str, text: str) -> str:
    return f"# {title}\n\n{text.strip()}\n"


def compose_brief(parts: BriefParts) -> str:
    sections = []
    if parts.progress is not None:
        sections.append((PROGRESS_SECTION, parts.progress))
    sections.append((f"Procedure {parts.procedure}", parts.procedure_body))
    if parts.arguments:
        lines = "\n".join(f"{key}{ARGUMENT_SEPARATOR}{value}" for key, value in parts.arguments.items())
        sections.append(("Arguments", lines))
    if parts.brief is not None:
        sections.append(("Brief", parts.brief))
    sections.append(("Progress file", parts.progress_description))
    sections.append(("Budget", f"{parts.budget} steps, the cap of your role for this segment."))
    sections.append(("End of segment", END_OF_SEGMENT))
    return "\n".join(_render_section(title, text) for title, text in sections)
