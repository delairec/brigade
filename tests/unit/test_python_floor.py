import unittest

from brigade.python_floor import describe_python_floor_breach


class PythonFloorTest(unittest.TestCase):
    def test_should_name_the_floor_and_the_running_version_below_it(self):
        rows = [
            ((3, 10, 14), "brigade needs Python 3.11 or later; this is Python 3.10.14"),
            ((3, 9, 0), "brigade needs Python 3.11 or later; this is Python 3.9.0"),
        ]
        for running_version, expected_breach in rows:
            with self.subTest(running_version=running_version):
                # Act
                breach = describe_python_floor_breach(running_version)

                # Assert
                self.assertEqual(breach, expected_breach)


class PythonFloorWhenTheRunningVersionReachesItTest(unittest.TestCase):
    def test_should_describe_no_breach(self):
        no_breach = None
        rows = [(3, 11, 0), (3, 13, 5)]
        for running_version in rows:
            with self.subTest(running_version=running_version):
                # Act
                breach = describe_python_floor_breach(running_version)

                # Assert
                self.assertEqual(breach, no_breach)
