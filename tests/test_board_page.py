import re
import unittest
from pathlib import Path

BOARD_PAGE_PATH = Path(__file__).resolve().parent.parent / "artifact" / "index.html"
CONTROL_TAGS = "select|input|textarea|button"


def read_board_page():
    return BOARD_PAGE_PATH.read_text(encoding="utf-8")


def extract_script(page):
    return re.search(r"<script>(.*?)</script>", page, re.S).group(1)


def extract_style(page):
    return re.search(r"<style>(.*?)</style>", page, re.S).group(1)


def extract_markup(page):
    return re.sub(r"<(script|style)>.*?</\1>", "", page, flags=re.S)


def find_status_mapping_keys(page):
    mappings = re.findall(r"\{([^{}]*['\"]?\bdraft['\"]?\s*:[^{}]*)\}", extract_script(page))
    return re.findall(r"['\"]?(\w+)['\"]?\s*:", " ".join(mappings))


def find_literal_status_comparisons(page):
    return re.findall(
        r"\.status\s*[!=]==?\s*['\"][^'\"]*['\"]|['\"][^'\"]*['\"]\s*[!=]==?\s*[\w.]*\.status\b",
        extract_script(page),
    )


def find_words_in_page(page, words):
    script_literals = re.findall(r"'((?:[^'\\]|\\.)*)'", extract_script(page))
    style_classes = re.findall(r"\.([A-Za-z][\w-]*)", extract_style(page))
    attribute_values = re.findall(r"\b(?:class|value)=\"([^\"]*)\"", extract_markup(page))
    page_text = " ".join(script_literals + style_classes + attribute_values)
    return set(re.findall(r"[A-Za-z]+", page_text)) & words


def collect_written_payloads(page):
    script = extract_script(page)
    literal_payloads = re.findall(r"\.(?:update|set|add)\(\s*\{([^}]*)\}", script)
    return {
        "fields": sorted(set(re.findall(r"(\w+)\s*:", " ".join(literal_payloads)))),
        "payloads_not_written_out": re.findall(r"\.(?:update|set|add)\(\s*(?!\{)([^,)]+)", script),
    }


def collect_controls(page):
    script = extract_script(page)
    return {
        "markup": re.findall(rf"<({CONTROL_TAGS})\b[^>]*?\bid=\"([^\"]*)\"", extract_markup(page)),
        "markup_without_id": re.findall(rf"<(?:{CONTROL_TAGS})\b(?![^>]*\bid=)[^>]*>", extract_markup(page)),
        "built_by_script": re.findall(rf"(?:el|createElement)\(\s*'({CONTROL_TAGS})'", script),
        "written_as_html_by_script": re.findall(rf"<(?:{CONTROL_TAGS})\b", script),
    }


class BoardPageTest(unittest.TestCase):
    def test_should_declare_the_corpus_statuses_in_one_mapping(self):
        # Arrange
        page = read_board_page()

        # Act
        mapping_keys = find_status_mapping_keys(page)

        # Assert
        self.assertEqual(mapping_keys, ["draft", "todo", "implemented", "archived"])

    def test_should_judge_a_task_status_by_its_mapping_and_no_word_of_its_own(self):
        # Arrange
        page = read_board_page()

        # Act
        literal_comparisons = find_literal_status_comparisons(page)

        # Assert
        self.assertEqual(literal_comparisons, [])

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
        written = collect_written_payloads(page)

        # Assert
        self.assertEqual(written, {"fields": ["notes", "updated_at", "updated_by"], "payloads_not_written_out": []})

    def test_should_offer_the_filters_the_search_and_the_task_actions_as_its_only_controls(self):
        # Arrange
        page = read_board_page()

        # Act
        controls = collect_controls(page)

        # Assert
        self.assertEqual(
            controls,
            {
                "markup": [("select", "f-milestone"), ("select", "f-status"), ("select", "f-role"), ("input", "f-search")],
                "markup_without_id": [],
                "built_by_script": ["textarea", "button", "textarea", "button", "button"],
                "written_as_html_by_script": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
