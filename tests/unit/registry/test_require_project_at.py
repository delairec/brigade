import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.registry.require_project_at import require_project_at

SHOP = Entity(name="shop", fields=(EntityField(name="PATH", value="/srv/shop"),))


class RequireProjectAtTest(unittest.TestCase):
    def test_should_answer_the_project_registered_at_the_path(self):
        # Act
        project = require_project_at((SHOP,), Path("/srv/shop"))

        # Assert
        self.assertEqual(project.name, "shop")

    def test_should_refuse_a_path_no_project_is_registered_at(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            require_project_at((SHOP,), Path("/srv/tidepool"))

        # Assert
        self.assertEqual(str(refusal.exception), "no registered project at /srv/tidepool")
