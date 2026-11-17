from collections.abc import Iterable
from pathlib import Path

from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from tests.guards.find_glossary_defects import GlossarySources
from tests.guards.list_command_paths import list_command_paths
from tests.guards.list_schema_words import list_schema_words
from tests.guards.read_task_milestones import read_task_milestones

CODE_SUFFIXES = (".py", ".md", ".toml", ".tpl", ".html", ".js", ".css")


def _read_texts(paths: Iterable[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(paths))


def read_glossary_sources(repository: Path) -> GlossarySources:
    corpus = _read_texts((repository / "corpus").glob("*.awawa"))
    code = _read_texts(path for path in (repository / "brigade").rglob("*") if path.suffix in CODE_SUFFIXES)
    return GlossarySources(
        task_milestones=read_task_milestones(corpus),
        command_paths=list_command_paths(),
        schema_words=list_schema_words(SHIPPED_SCHEMA.read_text(encoding="utf-8")),
        carried_text=f"{code}\n{corpus}",
    )
