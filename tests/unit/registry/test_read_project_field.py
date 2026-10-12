import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.read_project_field import read_project_field

NO_PROJECT = None
CLIENT_FIELD = "CLIENT"
PATH_FIELD = "PATH"


def _create_project(*fields: EntityField) -> Entity:
    return Entity(name="brigade", fields=fields)


class ReadProjectFieldTest(unittest.TestCase):
    def test_should_read_the_first_value_of_the_field(self):
        # Arrange
        project = _create_project(
            EntityField(name=CLIENT_FIELD, value="fake"),
            EntityField(name=PATH_FIELD, value="/srv/brigade"),
            EntityField(name=CLIENT_FIELD, value="other"),
        )

        # Act
        client = read_project_field(project, CLIENT_FIELD)

        # Assert
        self.assertEqual(client, "fake")

    def test_should_read_nothing_when_the_project_is_absent_or_lacks_the_field(self):
        # Arrange
        rows = [
            ("no project", NO_PROJECT, CLIENT_FIELD),
            ("no such field", _create_project(EntityField(name=PATH_FIELD, value="/srv/brigade")), CLIENT_FIELD),
        ]
        for case, project, field_name in rows:
            with self.subTest(case=case):
                # Act
                value = read_project_field(project, field_name)

                # Assert
                self.assertIsNone(value)
