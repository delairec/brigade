import unittest

from brigade.system.entry_detection import EntryDetection


class EntryDetectionTest(unittest.TestCase):
    def test_should_read_whether_the_document_holds_an_entry(self):
        # Act
        detection = EntryDetection.from_document({"schema_version": 1, "holds_entry": True})

        # Assert
        self.assertEqual(detection, EntryDetection(holds_entry=True))
