import unittest

from brigade.python_floor import refuse_python_below_floor


class PythonFloorTest(unittest.TestCase):
    def test_should_refuse_to_run_naming_the_floor_and_the_running_version_below_it(self):
        rows = [
            ((3, 10, 14), "brigade needs Python 3.11 or later; this is Python 3.10.14"),
            ((3, 9, 0), "brigade needs Python 3.11 or later; this is Python 3.9.0"),
        ]
        for running_version, expected_refusal in rows:
            with self.subTest(running_version=running_version):
                # Act
                with self.assertRaises(SystemExit) as refusal:
                    refuse_python_below_floor(running_version)

                # Assert
                self.assertEqual(refusal.exception.code, expected_refusal)


class PythonFloorWhenTheRunningVersionReachesItTest(unittest.TestCase):
    def test_should_let_brigade_run(self):
        let_through = None
        rows = [(3, 11, 0), (3, 13, 5)]
        for running_version in rows:
            with self.subTest(running_version=running_version):
                # Act
                outcome = refuse_python_below_floor(running_version)

                # Assert
                self.assertEqual(outcome, let_through)
