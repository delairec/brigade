import unittest

from brigade.dashboard.render_reports_fragment import render_reports_fragment


class RenderReportsFragmentTest(unittest.TestCase):
    def test_should_link_each_report_to_its_view_and_escape_its_strings(self):
        # Arrange
        document = {
            "schema_version": 1,
            "reports": [
                {"id": "oak_w3", "kind": "wave-report", "project": "oak"},
                {"id": "<i>x</i>", "kind": "study-answer", "project": None},
            ],
        }

        # Act
        fragment = render_reports_fragment(document)

        # Assert
        self.assertEqual(
            fragment,
            "<table><thead><tr><th>id</th><th>kind</th><th>project</th></tr></thead><tbody>"
            '<tr><td><a href="#reports/oak_w3">oak_w3</a></td><td>wave-report</td><td>oak</td></tr>'
            '<tr><td><a href="#reports/%3Ci%3Ex%3C%2Fi%3E">&lt;i&gt;x&lt;/i&gt;</a></td>'
            "<td>study-answer</td><td>-</td></tr>"
            "</tbody></table>",
        )

    def test_should_say_there_is_no_report(self):
        # Arrange
        document = {"schema_version": 1, "reports": []}

        # Act
        fragment = render_reports_fragment(document)

        # Assert
        self.assertEqual(fragment, "<p>no report</p>")
