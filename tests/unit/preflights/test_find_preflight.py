import unittest

from brigade.errors import BrigadeError
from brigade.preflights.find_preflight import find_preflight

PROJECT_NIGHTLY = {"name": "nightly", "description": "the nightly of the project"}
MACHINE_NIGHTLY = {"name": "nightly", "description": "the nightly of the machine"}
BUILT_IN_NIGHTLY = {"name": "nightly", "description": "the nightly of brigade"}


def hold_nothing(name: str) -> None:
    return None


def hold_project_nightly(name: str) -> dict:
    return PROJECT_NIGHTLY


def hold_machine_nightly(name: str) -> dict:
    return MACHINE_NIGHTLY


def hold_built_in_nightly(name: str) -> dict:
    return BUILT_IN_NIGHTLY


class FindPreflightTest(unittest.TestCase):
    def test_should_take_the_preflight_of_the_first_place_holding_it(self):
        # Arrange
        rows = [
            ((hold_project_nightly, hold_machine_nightly, hold_built_in_nightly), PROJECT_NIGHTLY),
            ((hold_nothing, hold_machine_nightly, hold_built_in_nightly), MACHINE_NIGHTLY),
            ((hold_nothing, hold_nothing, hold_built_in_nightly), BUILT_IN_NIGHTLY),
        ]
        for places, expected in rows:
            with self.subTest(expected=expected["description"]):
                # Act
                preflight = find_preflight("nightly", places)

                # Assert
                self.assertEqual(preflight, expected)

    def test_should_refuse_a_name_no_place_holds_naming_it(self):
        # Arrange
        no_place_holds_it = (hold_nothing, hold_nothing, hold_nothing)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            find_preflight("nightly", no_place_holds_it)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "no preflight nightly in the project, in the machine's preflights directory or among the built-ins",
        )
