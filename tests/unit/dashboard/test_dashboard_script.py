import unittest
from importlib.resources import files

SCRIPT = (files("brigade.dashboard") / "data" / "dashboard.js").read_text(encoding="utf-8")


class DashboardScriptTest(unittest.TestCase):
    def test_should_show_a_refused_post_in_the_page_and_never_in_an_alert(self):
        # Assert
        self.assertNotIn("window.alert", SCRIPT)
        self.assertIn('document.getElementById("notice")', SCRIPT)

    def test_should_poll_every_region_of_the_page(self):
        # Assert
        self.assertIn('document.querySelectorAll("[data-region]")', SCRIPT)

    def test_should_keep_the_open_details_and_the_focus_across_a_swap(self):
        # Assert
        self.assertIn('querySelectorAll("details[open] > summary")', SCRIPT)
        self.assertIn("document.activeElement", SCRIPT)
