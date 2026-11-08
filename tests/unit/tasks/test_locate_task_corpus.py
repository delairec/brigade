import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.tasks.locate_task_corpus import locate_task_corpus
from brigade.tasks.locate_task_worktree import TaskWorktree


class LocateTaskCorpusTest(unittest.TestCase):
    def test_should_answer_the_folder_awawa_reads_in_the_worktree(self):
        for fields, expected in [
            ((EntityField(name="CORPUS", value="corpus"),), Path("/srv/oak-b12")),
            (
                (EntityField(name="CORPUS", value="brigade"), EntityField(name="MODE", value="area")),
                Path("/srv/oak-b12/brigade"),
            ),
        ]:
            with self.subTest(fields=fields):
                # Arrange
                worktree = TaskWorktree(
                    path=Path("/srv/oak-b12"),
                    task="B12",
                    project=Entity(name="oak", fields=fields),
                    wave="oak_w1",
                    base="integration/harvest",
                )

                # Act
                corpus = locate_task_corpus(worktree)

                # Assert
                self.assertEqual(corpus, expected)
