import unittest

from brigade.dashboard.render_corpus_view import render_corpus_view
from tests.unit.dashboard.forms_collector import FormsCollector

TREE_OF_OAK = {
    "project": "oak",
    "ref": "main",
    "sha": "de446f3",
    "kind": "archive",
    "root": "/cache/refs/oak/de446f3",
}
B27 = {
    "target": "@TASK.B27",
    "status": "implemented",
    "file": "corpus/tasks.awawa",
    "line": 12,
    "ide_link": "idea://open?file=/cache/refs/oak/de446f3/corpus/tasks.awawa&line=12",
}
B30_WITHOUT_IDE_LINK = {
    "target": "@TASK.B30",
    "status": "todo",
    "file": "corpus/tasks.awawa",
    "line": 40,
    "ide_link": None,
}
TASKS_OF_OAK = TREE_OF_OAK | {
    "type": "TASK",
    "types": ["MILESTONE", "TASK"],
    "entities": [B27, B30_WITHOUT_IDE_LINK],
    "awawa_web": "http://127.0.0.1:7878/",
}
MARKUP = '"><script>alert(1)</script>'


def collect_forms(fragment: str) -> FormsCollector:
    collector = FormsCollector()
    collector.feed(fragment)
    return collector


class RenderCorpusViewOfTheTreeTest(unittest.TestCase):
    def test_should_link_an_entity_to_its_line_its_dependencies_and_awawa_web(self):
        # Act
        fragment = render_corpus_view(TASKS_OF_OAK)

        # Assert
        self.assertIn(
            '<li><a href="#corpus/oak?ref=main&amp;type=TASK&amp;entity=%40TASK.B27">@TASK.B27</a> implemented'
            ' <a href="idea://open?file=/cache/refs/oak/de446f3/corpus/tasks.awawa&amp;line=12">'
            "corpus/tasks.awawa:12</a>"
            ' <a href="http://127.0.0.1:7878/">awawa-web</a></li>',
            fragment,
        )

    def test_should_name_the_line_without_a_link_when_the_entity_carries_none(self):
        # Arrange
        without_awawa_web = TASKS_OF_OAK | {"awawa_web": None}

        # Act
        fragment = render_corpus_view(without_awawa_web)

        # Assert
        self.assertIn(
            '<li><a href="#corpus/oak?ref=main&amp;type=TASK&amp;entity=%40TASK.B30">@TASK.B30</a> todo'
            " corpus/tasks.awawa:40</li>",
            fragment,
        )

    def test_should_show_the_selector_alone_before_a_type_is_chosen(self):
        # Act
        fragment = render_corpus_view(TREE_OF_OAK)

        # Assert
        self.assertEqual(
            fragment,
            '<form class="corpus-selector" method="get">'
            '<label>project <select name="project"><option value="oak">oak</option></select></label>'
            '<label>ref <input name="ref" value="main"></label>'
            '<label>type <input name="type" list="corpus-types" value=""></label>'
            '<datalist id="corpus-types"></datalist>'
            '<label>board field <input name="field" value=""></label>'
            "<button>read</button></form>"
            "<p>de446f3</p>",
        )


    def test_should_offer_the_types_of_the_corpus_in_the_selector(self):
        # Act
        fragment = render_corpus_view(TASKS_OF_OAK)

        # Assert
        self.assertIn(
            '<datalist id="corpus-types"><option value="MILESTONE"></option><option value="TASK"></option></datalist>',
            fragment,
        )

class RenderCorpusViewOfTheBoardTest(unittest.TestCase):
    def test_should_show_every_task_under_its_status(self):
        # Arrange
        board = TASKS_OF_OAK | {
            "field": "STATUS",
            "board": [
                {"value": "implemented", "targets": ["@TASK.B27"]},
                {"value": "todo", "targets": ["@TASK.B30", "@TASK.B31"]},
            ],
        }

        # Act
        fragment = render_corpus_view(board)

        # Assert
        self.assertIn(
            '<section class="board"><h2>STATUS</h2>'
            "<div><h3>implemented</h3><ul><li>@TASK.B27</li></ul></div>"
            "<div><h3>todo</h3><ul><li>@TASK.B30</li><li>@TASK.B31</li></ul></div></section>",
            fragment,
        )

    def test_should_name_the_column_of_the_entities_without_the_field(self):
        # Arrange
        board = TASKS_OF_OAK | {"field": "MILESTONE", "board": [{"value": None, "targets": ["@TASK.B30"]}]}

        # Act
        fragment = render_corpus_view(board)

        # Assert
        self.assertIn("<div><h3>no MILESTONE</h3><ul><li>@TASK.B30</li></ul></div>", fragment)


class RenderCorpusViewOfTheDependenciesTest(unittest.TestCase):
    def test_should_show_what_the_entity_reaches_and_what_references_it(self):
        # Arrange
        dependencies = TASKS_OF_OAK | {
            "awawa_web": None,
            "dependencies": {"entity": "@TASK.B30", "reaches": [B27], "referenced_by": ["@TASK.B32"]},
        }

        # Act
        fragment = render_corpus_view(dependencies)

        # Assert
        self.assertIn(
            '<section class="dependencies"><h2>@TASK.B30</h2><h3>reaches</h3><ul>'
            '<li><a href="#corpus/oak?ref=main&amp;type=TASK&amp;entity=%40TASK.B27">@TASK.B27</a> implemented'
            ' <a href="idea://open?file=/cache/refs/oak/de446f3/corpus/tasks.awawa&amp;line=12">'
            "corpus/tasks.awawa:12</a></li>"
            "</ul><h3>referenced by</h3><ul><li>@TASK.B32</li></ul></section>",
            fragment,
        )


class RenderCorpusViewReadOnlyTest(unittest.TestCase):
    def test_should_hold_no_control_that_writes(self):
        # Arrange
        everything = TASKS_OF_OAK | {
            "field": "STATUS",
            "board": [{"value": "todo", "targets": ["@TASK.B30"]}],
            "dependencies": {"entity": "@TASK.B30", "reaches": [B27], "referenced_by": ["@TASK.B32"]},
        }

        # Act
        collector = collect_forms(render_corpus_view(everything))

        # Assert
        self.assertEqual(collector.methods, ["get"])
        self.assertEqual(collector.writing_attributes, [])


class RenderCorpusViewEscapingTest(unittest.TestCase):
    def test_should_escape_every_string_of_the_document(self):
        # Arrange
        entity = {"target": MARKUP, "status": MARKUP, "file": MARKUP, "line": 1, "ide_link": MARKUP}
        document = {
            "project": MARKUP,
            "ref": MARKUP,
            "sha": MARKUP,
            "type": MARKUP,
            "types": [MARKUP],
            "entities": [entity],
            "awawa_web": MARKUP,
            "field": MARKUP,
            "board": [{"value": MARKUP, "targets": [MARKUP]}],
            "dependencies": {"entity": MARKUP, "reaches": [entity], "referenced_by": [MARKUP]},
        }

        # Act
        fragment = render_corpus_view(document)

        # Assert
        self.assertNotIn("<script>", fragment)
