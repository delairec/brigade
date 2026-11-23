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

    def test_should_poll_at_the_interval_the_server_writes_into_the_page(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            "const POLL_INTERVAL_MS = Number("
            "document.querySelector('meta[name=\"brigade-poll-interval-ms\"]').content);",
            script,
        )
        self.assertNotIn("5000", script)

    def test_should_mark_a_wait_busy_only_once_it_lasts_300_ms_and_clear_it_when_the_wait_ends(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn("const BUSY_DELAY_MS = 300;\n", script)
        self.assertIn(
            "async function waitVisibly(element, wait) {\n"
            '  const shown = window.setTimeout(() => element.setAttribute("aria-busy", "true"), BUSY_DELAY_MS);\n'
            "  try {\n"
            "    return await wait;\n"
            "  } finally {\n"
            "    window.clearTimeout(shown);\n"
            '    element.removeAttribute("aria-busy");\n'
            "  }\n"
            "}\n",
            script,
        )

    def test_should_show_the_view_busy_on_a_navigation_the_user_chose_and_never_on_the_poll(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            'function showChosenView() {\n  return waitVisibly(document.getElementById("view"), showRegions());\n}\n',
            script,
        )
        self.assertIn('window.addEventListener("hashchange", showChosenView);', script)
        self.assertIn("    return;\n  }\n  showRegions();\n}\n", script)

    def test_should_hold_every_post_button_of_an_address_disabled_until_its_request_and_the_refresh_end(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            "function markPendingPosts() {\n"
            '  for (const button of document.querySelectorAll("button[data-post]")) {\n'
            "    button.disabled = pendingPosts.has(button.dataset.post);\n"
            "  }\n"
            "}\n",
            script,
        )
        self.assertIn(
            "  pendingPosts.add(address);\n"
            "  markPendingPosts();\n"
            "  try {\n"
            '    const response = await fetch(address, { method: "POST", headers: { [TOKEN_HEADER]: readToken() } });\n'
            '    showNotice(response.ok ? "" : (await response.json()).error);\n'
            "    await showRegions();\n"
            "  } catch {\n"
            "    showNotice(`The dashboard server did not answer ${address}.`);\n"
            "  } finally {\n"
            "    pendingPosts.delete(address);\n"
            "    markPendingPosts();\n"
            "  }\n",
            script,
        )
        self.assertIn('  await waitVisibly(document.getElementById("view"), sendPost(button.dataset.post));\n', script)

    def test_should_keep_a_pending_post_button_disabled_across_a_swap(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn("  shownFragments.set(region, fragment);\n  markPendingPosts();\n", script)

    def test_should_hold_the_refresh_button_of_the_next_tick_disabled_and_its_section_busy_while_it_reads(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            "  button.disabled = true;\n"
            '  await waitVisibly(button.closest(".next-tick"), readNextTick());\n'
            "  button.disabled = false;\n",
            script,
        )
        self.assertIn("  return showRegion(region, region.dataset.nextTick);\n", script)

    def test_should_compare_the_four_days_picked_as_soon_as_a_change_leaves_them_all_valid(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            "function submitRanges(event) {\n"
            '  const form = event.target.closest("form[data-ranges]");\n'
            '  if (form === null || event.target.type !== "date" || !form.checkValidity()) {\n'
            "    return;\n"
            "  }\n"
            "  const day = (name) => form.elements[name].value;\n"
            '  window.location.hash = `ledger?range=${day("before-start")}..${day("before-end")}'
            '&range=${day("after-start")}..${day("after-end")}`;\n'
            "}\n",
            script,
        )
        self.assertIn('document.addEventListener("change", submitRanges);', script)

    def test_should_say_in_the_notice_a_region_the_server_did_not_answer(self):
        # Act
        script = SCRIPT.read_text(encoding="utf-8")

        # Assert
        self.assertIn(
            "async function showRegion(region, path) {\n"
            "  try {\n"
            "    const response = await fetch(addProject(path));\n"
            "    swapFragment(region, await response.text());\n"
            "  } catch {\n"
            "    showNotice(`The dashboard server did not answer ${path}.`);\n"
            "  }\n"
            "}\n",
            script,
        )
