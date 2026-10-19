import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.render_project_entity import render_project_entity


class RenderProjectEntityTest(unittest.TestCase):
    def test_should_quote_every_field_but_the_status(self):
        # Arrange
        project = Entity(
            name="shop",
            fields=(EntityField(name="PATH", value='/srv/"shop"'), EntityField(name="STATUS", value="active")),
        )

        # Act
        text = render_project_entity(project)

        # Assert
        self.assertEqual(text, 'PROJECT shop\n\tPATH "/srv/\\"shop\\""\n\tSTATUS active\n')
