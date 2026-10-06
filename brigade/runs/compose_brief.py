from dataclasses import dataclass
from pathlib import Path

ARGUMENT_SEPARATOR = "="


@dataclass(frozen=True)
class BriefParts:
    progress: str | None
    procedure: str
    procedure_body: str
    arguments: dict
    brief: str | None
    progress_file: Path


def _render_section(title: str, text: str) -> str:
    return f"# {title}\n\n{text.strip()}\n"


def compose_brief(parts: BriefParts) -> str:
    sections = []
    if parts.progress is not None:
        sections.append(("Progress so far", parts.progress))
    sections.append((f"Procedure {parts.procedure}", parts.procedure_body))
    if parts.arguments:
        lines = "\n".join(f"{key}{ARGUMENT_SEPARATOR}{value}" for key, value in parts.arguments.items())
        sections.append(("Arguments", lines))
    if parts.brief is not None:
        sections.append(("Brief", parts.brief))
    sections.append(("Progress file", str(parts.progress_file)))
    return "\n".join(_render_section(title, text) for title, text in sections)
