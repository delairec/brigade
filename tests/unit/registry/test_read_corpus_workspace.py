import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import ToolFailure
from brigade.registry.read_corpus_workspace import read_corpus_workspace


class ReadCorpusWorkspaceTest(unittest.TestCase):
    def test_should_answer_the_folder_awawa_reads_in_each_mode(self):
        for fields, expected in [
            ((EntityField(name="CORPUS", value="corpus"),), Path()),
            ((EntityField(name="CORPUS", value="corpus"), EntityField(name="MODE", value="control")), Path()),
            ((EntityField(name="CORPUS", value="brigade"), EntityField(name="MODE", value="area")), Path("brigade")),
        ]:
            with self.subTest(fields=fields):
                # Arrange
                project = Entity(name="shop", fields=fields)

                # Act
                workspace = read_corpus_workspace(project)

                # Assert
                self.assertEqual(workspace, expected)

    def test_should_refuse_a_project_whose_corpus_mode_is_none(self):
        # Arrange
        project = Entity(name="shop", fields=(EntityField(name="MODE", value="none"),))

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            read_corpus_workspace(project)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.shop is in MODE none, which brigade does not deliver yet")
