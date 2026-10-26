import unittest

from brigade.inbox.is_signal_cited import is_signal_cited


class IsSignalCitedTest(unittest.TestCase):
    def test_should_tell_an_evidence_citing_the_fingerprint_whole_or_followed_by_a_space(self):
        # Arrange
        rows = (
            ("rt:101", "rt:101", True),
            ("rt:101 a thread on the cli", "rt:101", True),
            ("rt:1012 another thread", "rt:101", False),
            ("cr:oak:main:unit tests:def5678 failing", "cr:oak:main:unit tests:def5678", True),
            ("a thread rt:101", "rt:101", False),
        )
        for evidence, fingerprint, cited in rows:
            with self.subTest(evidence=evidence, fingerprint=fingerprint):
                # Act
                answer = is_signal_cited(evidence, fingerprint)

                # Assert
                self.assertIs(answer, cited)
