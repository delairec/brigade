import unittest

from brigade.corpus.locate_entity_block import locate_entity_block

TWO_PROJECTS = [
    "PROJECT shop\n",
    '\tPATH "/srv/shop"\n',
    "\n",
    "PROJECT depot\n",
    '\tPATH "/srv/depot"\n',
    "\tSTATUS active\n",
]


class LocateEntityBlockTest(unittest.TestCase):
    def test_should_locate_the_block_of_a_project_written_after_another(self):
        # Act
        block = locate_entity_block(TWO_PROJECTS, "PROJECT", "depot")

        # Assert
        self.assertEqual(block, range(3, 6))

    def test_should_locate_nothing_for_a_project_the_text_does_not_write(self):
        # Act
        block = locate_entity_block(TWO_PROJECTS, "PROJECT", "ghost")

        # Assert
        self.assertIsNone(block)
