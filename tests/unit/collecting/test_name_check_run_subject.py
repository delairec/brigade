import unittest

from brigade.collecting.name_check_run_subject import name_check_run_subject

CHECK_RUNS_AND_SUBJECTS = [
    ({"pull_request": 12, "branch": "task/oak_w1/B3"}, "12"),
    ({"pull_request": None, "branch": "main"}, "main"),
]


class NameCheckRunSubjectTest(unittest.TestCase):
    def test_should_name_the_check_run_by_its_pull_request_or_by_its_branch_without_one(self):
        for check_run, expected_subject in CHECK_RUNS_AND_SUBJECTS:
            with self.subTest(check_run=check_run):
                # Act
                subject = name_check_run_subject(check_run)

                # Assert
                self.assertEqual(subject, expected_subject)
