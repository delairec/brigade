import unittest

from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from tests.cli.temporary_machine import REPOSITORY_ROOT
from tests.guards.find_glossary_defects import GlossarySources, find_glossary_defects
from tests.guards.list_command_paths import list_command_paths
from tests.guards.list_schema_words import list_schema_words
from tests.guards.read_task_milestones import read_task_milestones

GLOSSARY_PAGE = REPOSITORY_ROOT / "wiki" / "Glossary.md"
CORPUS = REPOSITORY_ROOT / "corpus"
CODE = REPOSITORY_ROOT / "brigade"
CODE_SUFFIXES = (".py", ".md", ".toml", ".tpl", ".html", ".js", ".css")


def _read_texts(paths) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(paths) if path.is_file())


class GlossaryTest(unittest.TestCase):
    def test_should_hold_a_row_for_each_word_of_brigade_citing_the_task_that_delivers_it(self):
        # Arrange
        corpus = _read_texts(CORPUS.glob("*.awawa"))
        sources = GlossarySources(
            task_milestones=read_task_milestones(corpus),
            command_paths=list_command_paths(),
            schema_words=list_schema_words(SHIPPED_SCHEMA.read_text(encoding="utf-8")),
            carried_text=f"{_read_texts(path for path in CODE.rglob('*') if path.suffix in CODE_SUFFIXES)}\n{corpus}",
        )
        page = GLOSSARY_PAGE.read_text(encoding="utf-8")

        # Act
        defects = find_glossary_defects(page, sources)

        # Assert
        self.assertEqual(defects, [])
