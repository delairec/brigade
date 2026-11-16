import unittest

from brigade.dashboard.render_inbox_item import render_inbox_item


class RenderInboxItemTest(unittest.TestCase):
    def test_should_render_a_study_answer_under_its_kind_and_its_id_with_its_fields(self):
        # Arrange
        document = {
            "schema_version": 1,
            "answer": {
                "id": "disk_r2",
                "study": "disk",
                "project": "oak",
                "type": "ANSWER",
                "fields": [{"name": "SUMMARY", "value": "the disk <fills>"}],
            },
        }

        # Act
        fragment = render_inbox_item(document)

        # Assert
        self.assertEqual(
            fragment, "<h2>study-answer disk_r2</h2><dl><dt>SUMMARY</dt><dd>the disk &lt;fills&gt;</dd></dl>"
        )

    def test_should_render_a_signal_as_the_fields_of_its_document(self):
        # Arrange
        document = {"schema_version": 1, "signal": {"id": "a4a5f464", "kind": "note"}}

        # Act
        fragment = render_inbox_item(document)

        # Assert
        self.assertEqual(
            fragment,
            "<dl><dt>schema_version</dt><dd>1</dd><dt>signal</dt>"
            "<dd><dl><dt>id</dt><dd>a4a5f464</dd><dt>kind</dt><dd>note</dd></dl></dd></dl>",
        )
