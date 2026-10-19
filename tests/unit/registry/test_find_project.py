import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.registry.find_project import find_project

PROJECTS = (
    Entity(name="shop", fields=(EntityField(name="PATH", value="/srv/shop"),)),
    Entity(name="tidepool", fields=(EntityField(name="PATH", value="/srv/tidepool"),)),
)


class FindProjectTest(unittest.TestCase):
    def test_should_answer_the_project_of_that_name(self):
        # Act
        project = find_project(PROJECTS, "tidepool")

        # Assert
        self.assertEqual(project, Entity(name="tidepool", fields=(EntityField(name="PATH", value="/srv/tidepool"),)))

    def test_should_refuse_a_name_no_project_bears(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            find_project(PROJECTS, "ghost")

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.ghost is not registered")
