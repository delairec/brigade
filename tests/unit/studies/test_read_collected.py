import tempfile
import unittest
from pathlib import Path

from brigade.studies.read_collected import read_collected

RUN_ID = "20261019T090000Z-aaaaaa"


class ReadCollectedTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.run_directory = Path(directory.name) / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)

    def test_should_read_the_evidence_of_the_collect_steps_in_the_order_of_their_rank(self):
        # Arrange
        (self.run_directory / "steps" / "10-collect.json").write_text(
            '{"collected": [{"collector": "corpus", "summary": {}, "document": "/srv/corpus.json"}]}', encoding="utf-8"
        )
        (self.run_directory / "steps" / "2-collect.json").write_text(
            '{"collected": [{"collector": "ledger", "summary": {}, "document": "/srv/ledger.json"}]}', encoding="utf-8"
        )

        # Act
        collected = read_collected(self.run_directory)

        # Assert
        self.assertEqual(
            collected,
            [
                {"collector": "ledger", "summary": {}, "document": "/srv/ledger.json"},
                {"collector": "corpus", "summary": {}, "document": "/srv/corpus.json"},
            ],
        )
