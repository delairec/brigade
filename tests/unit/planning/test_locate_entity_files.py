import unittest

from brigade.planning.locate_entity_files import locate_entity_files
from brigade.planning.read_entity_sites import EntitySite


class LocateEntityFilesTest(unittest.TestCase):
    def test_should_locate_the_first_file_of_the_corpus_folder_holding_each_type(self):
        # Arrange
        sites = (
            EntitySite(type="TASK", name="B2", file="corpus/tasks-2.awawa", line=1),
            EntitySite(type="TASK", name="B1", file="corpus/tasks-1.awawa", line=1),
            EntitySite(type="MILESTONE", name="F0", file="docs/milestones.awawa", line=1),
        )

        # Act
        files = locate_entity_files(sites, "corpus")

        # Assert
        self.assertEqual(files, {"TASK": "corpus/tasks-1.awawa"})
