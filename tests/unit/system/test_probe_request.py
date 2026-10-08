import unittest

from brigade.system.probe_request import ProbeRequest


class ProbeRequestTest(unittest.TestCase):
    def test_should_write_the_document_of_a_probe(self):
        # Act
        document = ProbeRequest().to_document()

        # Assert
        self.assertEqual(document, {"schema_version": 1})
