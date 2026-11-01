import unittest

from brigade.studies.describe_mine_transcripts import describe_mine_transcripts
from tests.unit.studies.built_in_mine_transcripts import BUILT_IN_MINE_TRANSCRIPTS


class DescribeMineTranscriptsTest(unittest.TestCase):
    def test_should_describe_the_weekly_grouping_of_the_transcript_findings_into_patterns(self):
        # Act
        study = describe_mine_transcripts()

        # Assert
        self.assertEqual(study, BUILT_IN_MINE_TRANSCRIPTS)
