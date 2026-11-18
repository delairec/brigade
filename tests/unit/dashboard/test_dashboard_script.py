import unittest
from importlib.resources import files

SCRIPT = files("brigade.dashboard") / "data" / "dashboard.js"


class DashboardScriptTest(unittest.TestCase):
    def test_should_show_a_refused_post_in_the_page_and_never_in_an_alert(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertNotIn("window.alert", script)
        self.assertIn('document.getElementById("notice")', script)

    def test_should_poll_every_region_of_the_page(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn('document.querySelectorAll("[data-region]")', script)

    def test_should_keep_the_open_details_and_the_focus_across_a_swap(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn('querySelectorAll("details[open] > summary")', script)
        self.assertIn("document.activeElement", script)
