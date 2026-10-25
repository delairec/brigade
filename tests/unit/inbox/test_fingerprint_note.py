import unittest

from brigade.inbox.fingerprint_note import fingerprint_note


class FingerprintNoteTest(unittest.TestCase):
    def test_should_fingerprint_the_note_by_its_project_and_its_text(self):
        # Arrange
        rows = [
            ("a note on a project", "oak", "note:474fa40ae4db"),
            ("a note on no project", None, "note:57e52f352e5e"),
        ]
        for case, project, expected_fingerprint in rows:
            with self.subTest(case=case):
                # Act
                fingerprint = fingerprint_note(project, "fix the flaky test")

                # Assert
                self.assertEqual(fingerprint, expected_fingerprint)
