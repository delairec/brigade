import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

BOARD_PAGE_PATH = Path(__file__).resolve().parent.parent / "artifact" / "index.html"


class BoardPageSource(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script = ""
        self.style = ""
        self.attribute_values = []
        self._raw_text_tag = None

    def handle_starttag(self, tag, attrs):
        self.attribute_values.extend(value for name, value in attrs if name in ("class", "value") and value)
        self._raw_text_tag = tag if tag in ("script", "style") else None

    def handle_endtag(self, tag):
        self._raw_text_tag = None

    def handle_data(self, data):
        if self._raw_text_tag == "script":
            self.script += data
        elif self._raw_text_tag == "style":
            self.style += data


def read_board_page():
    page = BoardPageSource()
    page.feed(BOARD_PAGE_PATH.read_text(encoding="utf-8"))
    return page


def read_status_vocabulary(page):
    declaration = re.search(r"var STATUS_TONES = \{([^}]*)\}", page.script)
    if declaration is None:
        return []
    return re.findall(r"(\w+)\s*:", declaration.group(1))


def find_words_in_page(page, words):
    script_literals = re.findall(r"'((?:[^'\\]|\\.)*)'", page.script)
    style_classes = re.findall(r"\.([A-Za-z][\w-]*)", page.style)
    tokens = set()
    for text in script_literals + style_classes + page.attribute_values:
        tokens.update(re.findall(r"[A-Za-z]+", text))
    return tokens & words


def collect_written_fields(page):
    written_objects = re.findall(r"\.(?:update|set)\(\s*\{([^}]*)\}", page.script)
    fields = set()
    for written_object in written_objects:
        fields.update(re.findall(r"(\w+)\s*:", written_object))
    return fields


def count_created_selects(page):
    return len(re.findall(r"el\('select'", page.script))


class BoardPageTest(unittest.TestCase):
    def test_should_declare_the_corpus_statuses_as_its_vocabulary(self):
        # Arrange
        page = read_board_page()

        # Act
        vocabulary = read_status_vocabulary(page)

        # Assert
        self.assertEqual(vocabulary, ["draft", "todo", "implemented", "archived"])

    def test_should_hold_none_of_the_former_board_statuses(self):
        # Arrange
        page = read_board_page()
        former_board_statuses = {"doing", "review", "done", "blocked"}

        # Act
        leftovers = find_words_in_page(page, former_board_statuses)

        # Assert
        self.assertEqual(leftovers, set())

    def test_should_write_task_notes_and_never_the_status(self):
        # Arrange
        page = read_board_page()

        # Act
        written_fields = collect_written_fields(page)

        # Assert
        self.assertEqual(written_fields, {"notes", "updated_at", "updated_by"})

    def test_should_offer_no_control_that_edits_the_status(self):
        # Arrange
        page = read_board_page()

        # Act
        created_selects = count_created_selects(page)

        # Assert
        self.assertEqual(created_selects, 0)


if __name__ == "__main__":
    unittest.main()
