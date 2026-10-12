import datetime
import unittest

from brigade.system.name_toml_type import name_toml_type


class NameTomlTypeTest(unittest.TestCase):
    def test_should_name_the_toml_type_of_a_parsed_value(self):
        # Arrange
        rows = [
            ("a boolean", True, "a boolean"),
            ("an integer", 3, "an integer"),
            ("a float", 1.5, "a number"),
            ("a string", "fake", "a string"),
            ("a table", {"model": "opus"}, "a table"),
            ("an array", ["opus"], "an array"),
            ("a date", datetime.date(2026, 10, 7), "a date"),
            ("a time", datetime.time(12, 0), "a date"),
        ]
        for case, value, expected_name in rows:
            with self.subTest(case=case):
                # Act
                name = name_toml_type(value)

                # Assert
                self.assertEqual(name, expected_name)
