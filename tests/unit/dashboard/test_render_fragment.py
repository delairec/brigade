import unittest

from brigade.dashboard.render_fragment import render_fragment


class RenderFragmentTest(unittest.TestCase):
    def test_should_render_a_document_as_nested_lists_of_its_fields(self):
        # Arrange
        document = {"wave": "w4", "tasks": [{"task": "B27", "pull_request": None}], "ended": False}

        # Act
        fragment = render_fragment(document)

        # Assert
        self.assertEqual(
            fragment,
            "<dl><dt>wave</dt><dd>w4</dd>"
            "<dt>tasks</dt><dd><ol><li><dl><dt>task</dt><dd>B27</dd><dt>pull_request</dt><dd>None</dd></dl></li></ol></dd>"
            "<dt>ended</dt><dd>False</dd></dl>",
        )


class RenderFragmentOfStringsHoldingMarkupTest(unittest.TestCase):
    def test_should_leave_none_of_the_markup_in_the_fragment(self):
        # Arrange
        document = {
            "<b>field</b>": "<script>alert('wave')</script>",
            "reasons": ['<img src=x onerror="alert(1)">'],
        }

        # Act
        fragment = render_fragment(document)

        # Assert
        self.assertEqual(
            fragment,
            "<dl><dt>&lt;b&gt;field&lt;/b&gt;</dt><dd>&lt;script&gt;alert(&#x27;wave&#x27;)&lt;/script&gt;</dd>"
            "<dt>reasons</dt><dd><ol><li>&lt;img src=x onerror=&quot;alert(1)&quot;&gt;</li></ol></dd></dl>",
        )
