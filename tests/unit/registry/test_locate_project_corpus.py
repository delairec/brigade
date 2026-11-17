import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.locate_project_corpus import locate_project_corpus

UNREGISTERED = None


class LocateProjectCorpusTest(unittest.TestCase):
    def test_should_locate_the_corpus_of_a_project_in_control_or_area_and_none_otherwise(self):
        # Arrange
        rows = [
            ("control by default", Entity(name="shop", fields=()), Path()),
            ("control", Entity(name="shop", fields=(EntityField("MODE", "control"),)), Path()),
            (
                "area",
                Entity(name="shop", fields=(EntityField("MODE", "area"), EntityField("CORPUS", "brigade"))),
                Path("brigade"),
            ),
            ("none", Entity(name="shop", fields=(EntityField("MODE", "none"),)), None),
            ("unregistered", UNREGISTERED, None),
        ]
        for mode, project, expected in rows:
            with self.subTest(mode=mode):
                # Act
                corpus = locate_project_corpus(project)

                # Assert
                self.assertEqual(corpus, expected)
