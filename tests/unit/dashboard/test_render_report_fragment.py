import unittest

from brigade.dashboard.render_report_fragment import render_report_fragment


class RenderReportFragmentTest(unittest.TestCase):
    def test_should_render_the_fields_and_the_manual_tests_as_a_table_escaping_every_string(self):
        # Arrange
        document = {
            "schema_version": 1,
            "report": {
                "id": "oak_w3",
                "kind": "wave-report",
                "project": "oak",
                "type": "REPORT",
                "fields": [
                    {"name": "WAVE", "value": "oak_w3"},
                    {"name": "MANUAL_TEST", "value": "OK1: <script>alert(1)</script>"},
                    {"name": "NARRATIVE", "value": "<b>merged</b>"},
                ],
            },
        }

        # Act
        fragment = render_report_fragment(document)

        # Assert
        self.assertEqual(
            fragment,
            "<h2>wave-report oak_w3</h2>"
            "<dl><dt>WAVE</dt><dd>oak_w3</dd><dt>NARRATIVE</dt><dd>&lt;b&gt;merged&lt;/b&gt;</dd></dl>"
            "<h3>Manual tests</h3>"
            "<table><thead><tr><th>#</th><th>test</th></tr></thead>"
            "<tbody><tr><td>1</td><td>OK1: &lt;script&gt;alert(1)&lt;/script&gt;</td></tr></tbody></table>",
        )
