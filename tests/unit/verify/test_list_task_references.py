import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.verify.list_task_references import list_task_references

MOCKUP_RATIONALE = (
    "drawn in the mockup of the role max, the Artifact https://claude.ai/artifact/QYoFsx8Kq7LnSQrnKUJ7Je,"
    " version 2, its page Foundation"
)

SPECS_CLOSING_ON_PUNCTUATION = (
    ("the layout of https://example.org/harbour.", "https://example.org/harbour"),
    ("the mockup (https://example.org/harbour) is the contract", "https://example.org/harbour"),
    ("the mockup https://example.org/harbour; its page Tides", "https://example.org/harbour"),
)


class ListTaskReferencesTest(unittest.TestCase):
    def test_should_give_the_url_a_rationale_cites_with_the_line_that_says_what_it_covers(self):
        # Arrange
        task = Entity(
            name="B264",
            fields=(
                EntityField(name="TITLE", value="The dashboard gets its foundation"),
                EntityField(name="RATIONALE", value=MOCKUP_RATIONALE),
            ),
        )

        # Act
        references = list_task_references(task)

        # Assert
        self.assertEqual(
            references,
            [
                {
                    "url": "https://claude.ai/artifact/QYoFsx8Kq7LnSQrnKUJ7Je",
                    "field": "RATIONALE",
                    "line": MOCKUP_RATIONALE,
                }
            ],
        )

    def test_should_give_the_urls_of_the_acceptance_criteria_in_their_order(self):
        # Arrange
        task = Entity(
            name="T7",
            fields=(
                EntityField(name="SPEC", value="the page keeps the layout of https://example.org/harbour.html"),
                EntityField(name="SPEC", value="the tides read as on http://example.org/tides"),
            ),
        )

        # Act
        references = list_task_references(task)

        # Assert
        self.assertEqual(
            references,
            [
                {
                    "url": "https://example.org/harbour.html",
                    "field": "SPEC",
                    "line": "the page keeps the layout of https://example.org/harbour.html",
                },
                {
                    "url": "http://example.org/tides",
                    "field": "SPEC",
                    "line": "the tides read as on http://example.org/tides",
                },
            ],
        )

    def test_should_leave_the_punctuation_that_closes_the_sentence_out_of_the_url(self):
        for spec, url in SPECS_CLOSING_ON_PUNCTUATION:
            with self.subTest(spec=spec):
                # Arrange
                task = Entity(name="T7", fields=(EntityField(name="SPEC", value=spec),))

                # Act
                references = list_task_references(task)

                # Assert
                self.assertEqual(references, [{"url": url, "field": "SPEC", "line": spec}])

    def test_should_give_no_reference_for_a_url_cited_outside_the_criteria_and_the_rationale(self):
        # Arrange
        task = Entity(
            name="T7",
            fields=(
                EntityField(name="SPEC", value="the tide table lists seven days"),
                EntityField(name="SOURCE", value="the review of https://github.com/octo/tidepool/pull/12"),
            ),
        )
        no_reference = []

        # Act
        references = list_task_references(task)

        # Assert
        self.assertEqual(references, no_reference)
