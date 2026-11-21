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

    def test_should_read_the_next_tick_at_the_load_on_each_new_tick_and_on_its_refresh_button(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn('document.querySelector("[data-next-tick]")', script)
        self.assertIn('region.querySelector("time")', script)
        self.assertIn('event.target.closest("[data-refresh-next-tick]")', script)
        self.assertIn("readNextTick();\n", script)

    def test_should_read_the_next_tick_once_the_tick_seen_in_the_heartbeat_changes_and_never_on_the_poll(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            'const HEARTBEAT_UNREAD = Symbol("heartbeat unread");\nlet lastTickSeen = HEARTBEAT_UNREAD;\n', script
        )
        self.assertIn(
            "  const seen = tick === null ? null : tick.dateTime;\n"
            "  if (lastTickSeen !== HEARTBEAT_UNREAD && seen !== lastTickSeen) {\n"
            "    readNextTick();\n"
            "  }\n"
            "  lastTickSeen = seen;\n",
            script,
        )

    def test_should_show_the_next_tick_on_home_alone(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn('document.querySelector(".next-tick").hidden = selectView() !== FIRST_VIEW;', script)

    def test_should_keep_the_open_state_the_server_renders_for_a_details_the_replaced_fragment_did_not_show(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn("if (shownSummaries.has(summary.textContent))", script)
