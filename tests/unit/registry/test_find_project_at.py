import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.find_project_at import find_project_at

SHOP = Entity(name="shop", fields=(EntityField(name="PATH", value="/srv/shop"),))


class FindProjectAtTest(unittest.TestCase):
    def test_should_answer_the_project_registered_at_the_path(self):
        # Act
        project = find_project_at((SHOP,), Path("/srv/shop"))

        # Assert
        self.assertEqual(project, Entity(name="shop", fields=(EntityField(name="PATH", value="/srv/shop"),)))

    def test_should_answer_none_where_no_project_is_registered(self):
        # Act
        project = find_project_at((SHOP,), Path("/srv/tidepool"))

        # Assert
        self.assertIsNone(project)
