import unittest

from brigade.inbox.fingerprint_check_run import fingerprint_check_run

CHECK_RUNS_AND_FINGERPRINTS = [
    ({"pull_request": 12, "branch": "task/oak_w1/B3", "name": "tests", "head": "0123abc"}, "cr:oak:12:tests:0123abc"),
    ({"pull_request": None, "branch": "main", "name": "lint", "head": "4567def"}, "cr:oak:main:lint:4567def"),
]


class FingerprintCheckRunTest(unittest.TestCase):
    def test_should_fingerprint_the_check_run_by_its_pull_request_or_its_branch_its_name_and_its_head(self):
        for check_run, expected_fingerprint in CHECK_RUNS_AND_FINGERPRINTS:
            with self.subTest(check_run=check_run):
                # Act
                fingerprint = fingerprint_check_run("oak", check_run)

                # Assert
                self.assertEqual(fingerprint, expected_fingerprint)
