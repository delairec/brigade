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

    def test_should_group_the_views_of_its_rail_by_what_they_serve(self):
        # Act
        collector = collect_page_elements()

        # Assert
        self.assertEqual(
            collector.groups,
            [
                ("Operate", ["#status", "#waves", "#runs", "#inbox"]),
                ("Understand", ["#ledger", "#reports"]),
                ("Addons", ["#corpus"]),
            ],
        )

    def test_should_hold_the_project_selector_and_the_heartbeat_of_the_tick_as_regions_of_their_own(self):
        # Act
        collector = collect_page_elements()

        # Assert
        self.assertEqual(
            collector.regions,
            [
                (
                    "form",
                    {"class": "project-selector", "method": "get", "action": "/", "data-region": "/views/selector"},
                ),
                ("div", {"class": "heartbeat-region", "data-region": "/views/heartbeat"}),
            ],
        )

    def test_should_hold_the_next_tick_as_a_region_read_apart_from_the_poll_with_its_refresh_button(self):
        # Act
        page = PAGE.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            '<section class="next-tick" hidden><h2>Next tick</h2>'
            '<button type="button" data-refresh-next-tick>refresh</button>'
            '<div class="next-tick-decisions" data-next-tick="/views/next-tick"></div></section>',
            page,
        )

    def test_should_hold_the_notice_a_refused_post_is_shown_in(self):
        # Act
        collector = collect_page_elements()

        # Assert
        self.assertEqual(
            collector.alerts, [("p", {"id": "notice", "class": "notice", "role": "alert", "hidden": None})]
        )
