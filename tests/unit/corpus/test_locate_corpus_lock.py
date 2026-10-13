import unittest
from pathlib import Path

from brigade.corpus.locate_corpus_lock import locate_corpus_lock


class LocateCorpusLockTest(unittest.TestCase):
    def test_should_name_the_lock_after_the_path_of_the_repository(self):
        # Act
        lock = locate_corpus_lock(Path("/srv/state/brigade/locks"), Path("/srv/projects/shop"))

        # Assert
        self.assertEqual(lock, Path("/srv/state/brigade/locks/corpus-srv-projects-shop.lock"))
