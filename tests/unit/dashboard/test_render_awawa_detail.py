import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_detail import render_awawa_detail

DETAIL_OF_B1 = AwawaAddress(project="oak", parameters=(("view", "tree"), ("entity", "@TASK.B1")))
NO_FIELD = []
DOCUMENT = {
    "awawa_web": "http://127.0.0.1:7878/",
    "detail": {
        "entity": {
            "type": "TASK",
            "name": "B1",
            "file": "./corpus/tasks.awawa",
            "line": 3,
            "status": "todo",
            "fields": [
                {"name": "TITLE", "atoms": ['"Read <the> corpus"'], "fields": NO_FIELD},
                {
                    "name": "SPEC",
                    "atoms": ['"one"'],
                    "fields": [{"name": "IMPL", "atoms": ['"tests/a.py::x"'], "fields": NO_FIELD}],
                },
                {"name": "AFTER", "atoms": ["@TASK.B0"], "fields": NO_FIELD},
            ],
        },
        "references": [{"target": "@TASK.B0", "code": "B0", "label": "Start", "status": "implemented"}],
        "referenced_by": [{"target": "@TASK.B2", "code": "B2", "label": "Then", "status": "draft"}],
        "ide_link": "idea://open?file=/srv/oak/corpus/tasks.awawa&line=3",
    },
}


class RenderAwawaDetailTest(unittest.TestCase):
    def test_should_name_the_entity_and_close_the_panel_by_a_link(self):
        # Act
        fragment = render_awawa_detail(DOCUMENT, DETAIL_OF_B1)

        # Assert
        self.assertIn(
            '<aside class="awawa-detail"><header class="awawa-detail-head"><h2>'
            '<span class="dot tone-work" title="todo"></span>TASK B1</h2>'
            '<a class="awawa-close" href="#awawa/oak?view=tree">Close</a></header>'
            '<p class="awawa-place">./corpus/tasks.awawa:3</p>',
            fragment,
        )

    def test_should_show_the_fields_as_awawa_show_answers_them_escaped(self):
        # Act
        fragment = render_awawa_detail(DOCUMENT, DETAIL_OF_B1)

        # Assert
        self.assertIn(
            '<dl class="awawa-fields"><dt>TITLE</dt><dd>Read &lt;the&gt; corpus</dd><dt>SPEC</dt>'
            '<dd>one<dl class="awawa-fields"><dt>IMPL</dt><dd>tests/a.py::x</dd></dl></dd>'
            "<dt>AFTER</dt><dd>@TASK.B0</dd></dl>",
            fragment,
        )

    def test_should_link_the_entities_it_refers_to(self):
        # Act
        fragment = render_awawa_detail(DOCUMENT, DETAIL_OF_B1)

        # Assert
        self.assertIn(
            '<h3>Refers to</h3><ul class="awawa-neighbours"><li><a href="#awawa/oak?view=tree&amp;entity=%40TASK.B0">'
            '<span class="dot tone-done" title="implemented"></span><span class="awawa-code">B0</span>'
            ' <span class="awawa-label">Start</span></a></li></ul>',
            fragment,
        )

    def test_should_link_the_entities_referring_to_it(self):
        # Act
        fragment = render_awawa_detail(DOCUMENT, DETAIL_OF_B1)

        # Assert
        self.assertIn(
            '<h3>Referred to by</h3><ul class="awawa-neighbours"><li>'
            '<a href="#awawa/oak?view=tree&amp;entity=%40TASK.B2"><span class="dot tone-faint" title="draft"></span>',
            fragment,
        )

    def test_should_link_the_ide_and_awawa_web_when_the_document_carries_them(self):
        # Act
        fragment = render_awawa_detail(DOCUMENT, DETAIL_OF_B1)

        # Assert
        self.assertIn(
            '<p class="awawa-links"><a href="idea://open?file=/srv/oak/corpus/tasks.awawa&amp;line=3">'
            'Open in the IDE</a> <a href="http://127.0.0.1:7878/">Edit in awawa-web</a></p>',
            fragment,
        )

    def test_should_link_neither_when_the_document_carries_none(self):
        # Arrange
        without_links = {"awawa_web": None, "detail": DOCUMENT["detail"] | {"ide_link": None}}

        # Act
        fragment = render_awawa_detail(without_links, DETAIL_OF_B1)

        # Assert
        self.assertNotIn("awawa-links", fragment)

    def test_should_render_no_panel_when_the_address_names_no_entity(self):
        # Arrange
        without_detail = {"awawa_web": None}

        # Act
        fragment = render_awawa_detail(without_detail, DETAIL_OF_B1)

        # Assert
        self.assertEqual(fragment, "")
