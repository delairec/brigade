import unittest

from tests.cli.temporary_machine import REPOSITORY_ROOT
from tests.guards.find_glossary_defects import find_glossary_defects
from tests.guards.read_glossary_sources import read_glossary_sources

GLOSSARY_PAGE = REPOSITORY_ROOT / "wiki" / "Glossary.md"


class GlossaryTest(unittest.TestCase):
    def test_should_hold_a_row_for_each_word_of_brigade_citing_the_task_that_delivers_it(self):
        # Arrange
        sources = read_glossary_sources(REPOSITORY_ROOT)
        page = GLOSSARY_PAGE.read_text(encoding="utf-8")

        # Act
        defects = find_glossary_defects(page, sources)

        # Assert
        self.assertEqual(defects, [])
