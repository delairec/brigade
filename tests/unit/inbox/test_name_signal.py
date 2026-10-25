import unittest

from brigade.inbox.name_signal import name_signal


class NameSignalTest(unittest.TestCase):
    def test_should_name_the_signal_by_the_sha256_of_its_fingerprint(self):
        # Act
        signal_id = name_signal("note:2c26b46b68ff")

        # Assert
        self.assertEqual(signal_id, "c1778e1e344e1a4c576746c787e55129814c3e589ff099c9b1c502cc9aebc7e9")
