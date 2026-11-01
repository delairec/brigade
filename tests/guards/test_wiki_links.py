import tempfile
import unittest
from pathlib import Path

from tests.guards.find_wiki_link_defects import find_wiki_link_defects

WIKI_ROOT = Path(__file__).resolve().parents[2] / "wiki"
HOME_LINKING_RUNS = "- [Runs](Runs.md) — what a run keeps\n"
SIDEBAR_LINKING_HOME_AND_RUNS = "- [Home](Home.md)\n- [Runs](Runs.md)\n"
RUNS_PAGE = "Answers how a run is launched.\n"


class WikiLinksTest(unittest.TestCase):
    def test_should_find_no_link_defect_in_the_wiki_of_the_repository(self):
        # Act
        defects = find_wiki_link_defects(WIKI_ROOT)

        # Assert
        self.assertEqual(defects, [])


class WikiLinksGuardTest(unittest.TestCase):
    def inspect(self, pages: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as root:
            for name, text in pages.items():
                (Path(root) / name).write_text(text, encoding="utf-8")
            return find_wiki_link_defects(Path(root))

    def test_should_flag_a_link_to_a_page_the_wiki_lacks(self):
        # Arrange
        runs_page_linking_a_missing_page = "See [Ledger](Ledger.md).\n"

        # Act
        defects = self.inspect(
            {
                "Home.md": HOME_LINKING_RUNS,
                "_Sidebar.md": SIDEBAR_LINKING_HOME_AND_RUNS,
                "Runs.md": runs_page_linking_a_missing_page,
            }
        )

        # Assert
        self.assertEqual(defects, ["Runs.md links Ledger.md, which is no page of wiki/"])

    def test_should_flag_a_link_the_repository_view_does_not_resolve(self):
        # Arrange
        runs_page_linking_in_the_wiki_form = "Back to [Home](Home).\n"

        # Act
        defects = self.inspect(
            {
                "Home.md": HOME_LINKING_RUNS,
                "_Sidebar.md": SIDEBAR_LINKING_HOME_AND_RUNS,
                "Runs.md": runs_page_linking_in_the_wiki_form,
            }
        )

        # Assert
        self.assertEqual(defects, ["Runs.md links Home, which is no page of wiki/"])

    def test_should_flag_a_page_home_does_not_link(self):
        # Arrange
        home_linking_no_page = "brigade runs AI-agent waves.\n"

        # Act
        defects = self.inspect(
            {"Home.md": home_linking_no_page, "_Sidebar.md": SIDEBAR_LINKING_HOME_AND_RUNS, "Runs.md": RUNS_PAGE}
        )

        # Assert
        self.assertEqual(defects, ["Runs.md is not linked from Home.md"])

    def test_should_flag_a_page_the_sidebar_does_not_link(self):
        # Arrange
        sidebar_linking_home_alone = "- [Home](Home.md)\n"

        # Act
        defects = self.inspect(
            {"Home.md": HOME_LINKING_RUNS, "_Sidebar.md": sidebar_linking_home_alone, "Runs.md": RUNS_PAGE}
        )

        # Assert
        self.assertEqual(defects, ["Runs.md is not linked from _Sidebar.md"])

    def test_should_flag_a_missing_entry_page(self):
        for missing, pages, expected in [
            ("Home.md", {"_Sidebar.md": "- [Runs](Runs.md)\n", "Runs.md": RUNS_PAGE}, ["wiki/ has no Home.md"]),
            ("_Sidebar.md", {"Home.md": HOME_LINKING_RUNS, "Runs.md": RUNS_PAGE}, ["wiki/ has no _Sidebar.md"]),
        ]:
            with self.subTest(missing=missing):
                # Act
                defects = self.inspect(pages)

                # Assert
                self.assertEqual(defects, expected)

    def test_should_accept_links_to_pages_to_anchors_and_to_absolute_addresses(self):
        # Arrange
        runs_page_with_every_accepted_link = "See [the trail](Runs.md#trail), [above](#runs) and [the handoff](https://github.com/delairec/brigade/blob/main/HANDOFF.md).\n"

        # Act
        defects = self.inspect(
            {
                "Home.md": HOME_LINKING_RUNS,
                "_Sidebar.md": SIDEBAR_LINKING_HOME_AND_RUNS,
                "Runs.md": runs_page_with_every_accepted_link,
            }
        )

        # Assert
        self.assertEqual(defects, [])
