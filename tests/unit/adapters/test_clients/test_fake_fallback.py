import unittest

from brigade.adapters.test_clients.fake_fallback import answer


class FakeFallbackProbeTest(unittest.TestCase):
    def test_should_answer_under_the_name_of_the_fallback_client(self):
        # Act
        probe = answer("probe", {"schema_version": 1, "reasoning_table": {}, "settings": {}, "home": "/srv/agent"})

        # Assert
        self.assertEqual(probe["client"], "fake-fallback")
