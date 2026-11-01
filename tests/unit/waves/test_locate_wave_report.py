import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.waves.locate_wave_report import locate_wave_report

TIDEPOOL = Entity(name="tidepool", fields=(EntityField(name="CORPUS", value="spec"),))


class LocateWaveReportTest(unittest.TestCase):
    def test_should_name_the_report_after_the_number_of_the_wave_under_the_corpus(self):
        # Act
        report = locate_wave_report(TIDEPOOL, "tidepool_w16")

        # Assert
        self.assertEqual(report, "spec/waves/16-report.md")
