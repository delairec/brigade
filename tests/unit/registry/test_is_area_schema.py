import unittest

from brigade.registry.is_area_schema import is_area_schema
from brigade.registry.render_project_schema import render_area_schema

SCHEMA_OF_AN_EARLIER_AREA = (
    "SCHEMA MILESTONE\n\tFIELD TITLE string\n\n"
    "SCHEMA TASK\n\tFIELD SPEC string\n\t\tFIELD IMPL string\n\n"
    "SCHEMA DECISION\n\tFIELD TITLE string\n\n"
    "SCHEMA OPEN_QUESTION\n\tFIELD QUESTION string\n"
)


class IsAreaSchemaTest(unittest.TestCase):
    def test_should_recognise_the_schema_brigade_installs_in_an_area(self):
        # Arrange
        installed = render_area_schema()

        # Act
        recognised = is_area_schema(installed)

        # Assert
        self.assertIs(recognised, True)

    def test_should_recognise_the_schema_an_earlier_brigade_installed(self):
        # Act
        recognised = is_area_schema(SCHEMA_OF_AN_EARLIER_AREA)

        # Assert
        self.assertIs(recognised, True)

    def test_should_refuse_a_schema_that_is_not_the_one_of_an_area(self):
        for case, schema in [
            (
                "IMPL an anchor, as in control",
                "SCHEMA MILESTONE\n\nSCHEMA TASK\n\tFIELD SPEC string\n\t\tFIELD IMPL anchor\n\n"
                "SCHEMA DECISION\n\nSCHEMA OPEN_QUESTION\n",
            ),
            (
                "IMPL a string on another type than the task",
                "SCHEMA MILESTONE\n\nSCHEMA TASK\n\tFIELD SPEC string\n\n"
                "SCHEMA DECISION\n\tFIELD SPEC string\n\t\tFIELD IMPL string\n\nSCHEMA OPEN_QUESTION\n",
            ),
            (
                "a type brigade never declared",
                "SCHEMA MILESTONE\n\nSCHEMA TASK\n\tFIELD SPEC string\n\t\tFIELD IMPL string\n\n"
                "SCHEMA DECISION\n\nSCHEMA OPEN_QUESTION\n\nSCHEMA RULE\n",
            ),
            (
                "a type of the area missing",
                "SCHEMA MILESTONE\n\nSCHEMA TASK\n\tFIELD SPEC string\n\t\tFIELD IMPL string\n\nSCHEMA DECISION\n",
            ),
            ("no schema", ""),
        ]:
            with self.subTest(case=case):
                # Act
                recognised = is_area_schema(schema)

                # Assert
                self.assertIs(recognised, False)
