import unittest

from brigade.verify.list_task_references import list_task_references

MOCKUP = "artifact/harbour/index.html"


class ListTaskReferencesTest(unittest.TestCase):
    def test_should_give_each_reference_the_task_carries_with_what_it_covers_in_their_order(self):
        # Arrange
        task = {
            "fields": [
                {"name": "TITLE", "atoms": ['"The dashboard gets its foundation"'], "fields": []},
                {
                    "name": "REFERENCE",
                    "atoms": [f'"{MOCKUP}"'],
                    "fields": [{"name": "COVERS", "atoms": ['"version 2, its page Foundation"'], "fields": []}],
                },
                {
                    "name": "REFERENCE",
                    "atoms": ['"docs/harbour-mockup.html"'],
                    "fields": [{"name": "COVERS", "atoms": ['"its section Tides"'], "fields": []}],
                },
            ]
        }

        # Act
        references = list_task_references(task)

        # Assert
        self.assertEqual(
            references,
            [
                {"reference": MOCKUP, "covers": "version 2, its page Foundation"},
                {"reference": "docs/harbour-mockup.html", "covers": "its section Tides"},
            ],
        )

    def test_should_give_no_coverage_for_a_reference_that_states_none(self):
        # Arrange
        task = {"fields": [{"name": "REFERENCE", "atoms": [f'"{MOCKUP}"'], "fields": []}]}

        # Act
        references = list_task_references(task)

        # Assert
        self.assertEqual(references, [{"reference": MOCKUP, "covers": None}])

    def test_should_take_no_url_its_criteria_or_its_rationale_cite_for_a_reference(self):
        # Arrange
        task = {
            "fields": [
                {"name": "SPEC", "atoms": ['"the page keeps the layout of https://example.org/harbour"'], "fields": []},
                {"name": "RATIONALE", "atoms": [f'"drawn in the mockup {MOCKUP}, its page Foundation"'], "fields": []},
            ]
        }
        no_reference = []

        # Act
        references = list_task_references(task)

        # Assert
        self.assertEqual(references, no_reference)
