import unittest
from importlib.resources import files

from tests.unit.dashboard.page_elements_collector import PageElementsCollector

PAGE = files("brigade.dashboard") / "data" / "index.html"


def collect_page_elements() -> PageElementsCollector:
    collector = PageElementsCollector()
    collector.feed(PAGE.read_text(encoding="utf-8"))
    return collector


class DashboardPageTest(unittest.TestCase):
    def test_should_load_its_script_and_its_stylesheet_from_the_server(self):
        # Act
        collector = collect_page_elements()

        # Assert
        self.assertEqual(
            collector.loaded,
            [
                ("link", {"rel": "stylesheet", "href": "/dashboard.css"}),
                ("script", {"src": "/dashboard.js", "defer": None}),
            ],
        )

    def test_should_hold_no_inline_script_no_inline_style_and_no_style_attribute(self):
        # Act
        collector = collect_page_elements()

        # Assert
        self.assertEqual(collector.inline_scripts, [])
        self.assertEqual(collector.style_elements, [])
        self.assertEqual(collector.inline_attributes, [])

    def test_should_link_every_view_from_its_navigation(self):
        # Act
        collector = collect_page_elements()

        # Assert
        self.assertEqual(
            collector.view_links, ["#status", "#waves", "#inbox", "#corpus", "#ledger", "#reports", "#runs"]
        )
