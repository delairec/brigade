import unittest

from brigade.corpus.set_entity_status import set_entity_status

REGISTRY = 'PROJECT shop\n\tPATH "/srv/shop"\n\tSTATUS active\n'


class SetEntityStatusTest(unittest.TestCase):
    def test_should_answer_nothing_when_the_text_does_not_write_the_entity(self):
        # Act
        text = set_entity_status(REGISTRY, "PROJECT", "ghost", "paused")

        # Assert
        self.assertIsNone(text)

    def test_should_rewrite_the_status_line_of_the_entity(self):
        # Act
        text = set_entity_status(REGISTRY, "PROJECT", "shop", "paused")

        # Assert
        self.assertEqual(text, 'PROJECT shop\n\tPATH "/srv/shop"\n\tSTATUS paused\n')
