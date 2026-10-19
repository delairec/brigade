import unittest

from brigade.registry.remove_project_entity import remove_project_entity

REGISTRY = 'PROJECT shop\n\tPATH "/srv/shop"\n\tSTATUS active\n'


class RemoveProjectEntityTest(unittest.TestCase):
    def test_should_leave_the_text_as_it_is_when_it_does_not_write_the_project(self):
        # Act
        text = remove_project_entity(REGISTRY, "ghost")

        # Assert
        self.assertEqual(text, 'PROJECT shop\n\tPATH "/srv/shop"\n\tSTATUS active\n')

    def test_should_remove_the_block_of_the_project_and_keep_the_others(self):
        # Arrange
        registry = 'PROJECT shop\n\tPATH "/srv/shop"\n\nPROJECT tidepool\n\tPATH "/srv/tidepool"\n'

        # Act
        text = remove_project_entity(registry, "shop")

        # Assert
        self.assertEqual(text, 'PROJECT tidepool\n\tPATH "/srv/tidepool"\n')
