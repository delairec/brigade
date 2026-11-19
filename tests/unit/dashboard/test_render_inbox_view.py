import unittest

from brigade.dashboard.render_inbox_view import render_inbox_view

NOTE_ID = "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc"
THREAD_ID = "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f"
STALL_ID = "5c1e0d9b7a3f4e2d8c6b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d"
DISMISSED_ID = "0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e"
NOTE = {
    "id": NOTE_ID,
    "fingerprint": "note:474fa40ae4db",
    "kind": "note",
    "project": "oak",
    "count": 1,
    "age_s": 172800,
    "status": "new",
    "stale": False,
}
THREAD = {
    "id": THREAD_ID,
    "fingerprint": "rt:PRRT_kwDO",
    "kind": "review_thread",
    "project": None,
    "count": 3,
    "age_s": 3600,
    "status": "new",
    "stale": False,
}
EMPTY_INBOX = {"schema_version": 1, "signals": [], "families": [], "patterns": [], "answers": []}


def create_pattern(name: str, repeats: str | None, signals: list[str]) -> dict:
    return {
        "name": name,
        "title": f"the title of {name}",
        "action": "wave",
        "target": "oak",
        "recipe": None,
        "repeats": repeats,
        "signals": signals,
    }


class RenderInboxViewTest(unittest.TestCase):
    def test_should_open_on_one_sentence_and_four_tiles(self):
        # Arrange
        no_cited_signal = []
        document = {
            **EMPTY_INBOX,
            "signals": [NOTE, THREAD],
            "patterns": [
                create_pattern("FlakyTests", None, [NOTE_ID]),
                create_pattern("FlakyTestsAgain", "FlakyTests", no_cited_signal),
            ],
            "answers": [{"id": "disk_20261019T090000Z_b2", "study": "disk", "project": None}],
        }

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<p class="status-sentence">2 proposed patterns to decide first,'
                " then 2 new signals and 1 study answers to read.</p>"
                '<div class="stat-tiles">'
                '<div class="stat-tile"><span class="stat-value">2</span>'
                '<span class="stat-label">patterns to decide</span>'
                '<span class="stat-perimeter">1 of them repeats</span></div>'
                '<div class="stat-tile"><span class="stat-value">2</span>'
                '<span class="stat-label">new signals</span>'
                '<span class="stat-perimeter">1 covered by a pattern</span></div>'
                '<div class="stat-tile"><span class="stat-value">2d</span>'
                '<span class="stat-label">oldest signal</span>'
                '<span class="stat-perimeter">the age of the oldest new signal</span></div>'
                '<div class="stat-tile"><span class="stat-value">1</span>'
                '<span class="stat-label">study answers</span>'
                '<span class="stat-perimeter">to read</span></div>'
                "</div>"
            ),
            fragment,
        )

    def test_should_list_a_pattern_under_its_title_with_what_ratifying_it_starts_and_its_ratify_button_first(self):
        # Arrange
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [create_pattern("FlakyTests", None, [NOTE_ID])]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn(
            "<section><h2>Decide first</h2>"
            '<article class="pattern"><h3>the title of FlakyTests</h3>'
            '<p class="pattern-name"><a href="#inbox/FlakyTests"><code>FlakyTests</code></a></p>'
            "<p>If ratified: a request on oak, planned into a wave</p>"
            "<p>1 of the 1 signals it cites still new</p>"
            '<button data-post="/api/inbox/ratify/FlakyTests">ratify</button>'
            '<button data-post="/api/inbox/dismiss/FlakyTests">dismiss</button>'
            "</article></section>",
            fragment,
        )

    def test_should_count_the_signals_it_cites_that_are_still_new(self):
        # Arrange
        document = {
            **EMPTY_INBOX,
            "signals": [NOTE],
            "patterns": [create_pattern("FlakyTests", None, [NOTE_ID, DISMISSED_ID])],
        }

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn("<p>1 of the 2 signals it cites still new</p>", fragment)

    def test_should_offer_a_ratification_by_kind_for_a_pattern_becoming_a_constraint(self):
        # Arrange
        pattern = {**create_pattern("FlakyTests", None, []), "action": "constraint"}
        document = {**EMPTY_INBOX, "patterns": [pattern]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn(
            "<p>If ratified: a constraint on oak of the kind chosen, and a request delivering it</p>"
            "<p>0 of the 0 signals it cites still new</p>"
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=rule">ratify as rule</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=guard">ratify as guard</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=lint">ratify as lint</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=schema">ratify as schema</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=skill">ratify as skill</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=script">ratify as script</button>'
            '<button data-post="/api/inbox/dismiss/FlakyTests">dismiss</button>',
            fragment,
        )

    def test_should_say_ratifying_starts_nothing_until_a_pattern_acting_on_a_target_names_one(self):
        for action in ("wave", "constraint", "order"):
            with self.subTest(action=action):
                # Arrange
                pattern = {**create_pattern("FlakyTests", None, []), "action": action, "target": None}
                document = {**EMPTY_INBOX, "patterns": [pattern]}

                # Act
                fragment = render_inbox_view(document)

                # Assert
                self.assertIn("<p>If ratified: nothing until the pattern names a target</p>", fragment)

    def test_should_say_ratifying_an_order_starts_nothing_until_the_pattern_names_a_recipe(self):
        # Arrange
        pattern = {**create_pattern("StaleLocks", None, []), "action": "order", "recipe": None}
        document = {**EMPTY_INBOX, "patterns": [pattern]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn("<p>If ratified: nothing until the pattern names a recipe</p>", fragment)

    def test_should_say_ratifying_an_order_starts_an_order_of_the_recipe_it_names(self):
        # Arrange
        pattern = {**create_pattern("StaleLocks", None, []), "action": "order", "recipe": "clear-locks"}
        document = {**EMPTY_INBOX, "patterns": [pattern]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn("<p>If ratified: an order of the recipe clear-locks on oak</p>", fragment)

    def test_should_fold_two_repeats_under_the_pattern_they_name_each_with_its_buttons(self):
        # Arrange
        no_cited_signal = []
        document = {
            **EMPTY_INBOX,
            "patterns": [
                create_pattern("FlakyTests", None, no_cited_signal),
                create_pattern("FlakyTestsAgain", "FlakyTests", no_cited_signal),
                create_pattern("FlakyTestsOnceMore", "FlakyTests", no_cited_signal),
            ],
        }

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn(
            '<button data-post="/api/inbox/dismiss/FlakyTests">dismiss</button>'
            "<details><summary>2 repeats</summary>"
            '<article class="pattern"><h3>the title of FlakyTestsAgain</h3>'
            '<p class="pattern-name"><a href="#inbox/FlakyTestsAgain"><code>FlakyTestsAgain</code></a></p>'
            "<p>If ratified: a request on oak, planned into a wave</p>"
            "<p>0 of the 0 signals it cites still new</p>"
            '<button data-post="/api/inbox/ratify/FlakyTestsAgain">ratify</button>'
            '<button data-post="/api/inbox/dismiss/FlakyTestsAgain">dismiss</button></article>'
            '<article class="pattern"><h3>the title of FlakyTestsOnceMore</h3>'
            '<p class="pattern-name"><a href="#inbox/FlakyTestsOnceMore"><code>FlakyTestsOnceMore</code></a></p>'
            "<p>If ratified: a request on oak, planned into a wave</p>"
            "<p>0 of the 0 signals it cites still new</p>"
            '<button data-post="/api/inbox/ratify/FlakyTestsOnceMore">ratify</button>'
            '<button data-post="/api/inbox/dismiss/FlakyTestsOnceMore">dismiss</button></article>'
            "</details></article></section>",
            fragment,
        )

    def test_should_let_a_repeat_of_a_pattern_no_longer_proposed_stand_alone_naming_what_it_repeats(self):
        # Arrange
        no_cited_signal = []
        document = {**EMPTY_INBOX, "patterns": [create_pattern("FlakyTestsAgain", "FlakyTests", no_cited_signal)]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn(
            "<section><h2>Decide first</h2>"
            '<article class="pattern"><h3>the title of FlakyTestsAgain</h3>'
            '<p class="pattern-name"><a href="#inbox/FlakyTestsAgain"><code>FlakyTestsAgain</code></a>'
            " repeats <code>FlakyTests</code></p>",
            fragment,
        )

    def test_should_group_the_new_signals_by_what_recorded_them_each_linking_its_evidence(self):
        # Arrange
        other_note = {**NOTE, "id": DISMISSED_ID, "project": "elm"}
        document = {**EMPTY_INBOX, "signals": [NOTE, THREAD, other_note]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn(
            "<section><h2>New signals</h2>"
            "<section><h3>note</h3><ul>"
            f'<li><a href="#inbox/{NOTE_ID}"><code>a4a5f46</code></a> oak, 1 in 2d'
            f' <button data-post="/api/inbox/dismiss/{NOTE_ID}">dismiss</button></li>'
            f'<li><a href="#inbox/{DISMISSED_ID}"><code>0d1e2f3</code></a> elm, 1 in 2d'
            f' <button data-post="/api/inbox/dismiss/{DISMISSED_ID}">dismiss</button></li>'
            "</ul></section>"
            "<section><h3>review_thread</h3><ul>"
            f'<li><a href="#inbox/{THREAD_ID}"><code>19757dd</code></a> -, 3 in 1h'
            f' <button data-post="/api/inbox/dismiss/{THREAD_ID}">dismiss</button></li>'
            "</ul></section></section>",
            fragment,
        )

    def test_should_mark_stale_a_stall_whose_task_merged_since(self):
        # Arrange
        stall = {
            "id": STALL_ID,
            "fingerprint": "stall:oak:oak_w2:B17",
            "kind": "stall",
            "project": "oak",
            "count": 1,
            "age_s": 7200,
            "status": "new",
            "stale": True,
        }
        document = {**EMPTY_INBOX, "signals": [stall]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn(
            f'<li><a href="#inbox/{STALL_ID}"><code>5c1e0d9</code></a> oak, 1 in 2h'
            ' <span class="stale">stale: its task merged since</span>'
            f' <button data-post="/api/inbox/dismiss/{STALL_ID}">dismiss</button></li>',
            fragment,
        )

    def test_should_say_why_each_region_is_empty(self):
        # Act
        fragment = render_inbox_view(EMPTY_INBOX)

        # Assert
        self.assertIn(
            "<section><h2>Decide first</h2>"
            '<div class="empty-state"><p class="empty-why">no pattern waits for a decision</p>'
            '<p class="empty-fill">the daily triage proposes one from the new signals</p></div></section>'
            "<section><h2>New signals</h2>"
            '<div class="empty-state"><p class="empty-why">no new signal is in the inbox</p>'
            '<p class="empty-fill">a review thread, a stall, a check run, a note or a scan records one</p></div>'
            "</section>"
            "<section><h2>Study answers</h2>"
            '<div class="empty-state"><p class="empty-why">no study answer is to read</p>'
            '<p class="empty-fill">a study run writes one</p></div></section>',
            fragment,
        )

    def test_should_link_each_study_answer_to_its_view(self):
        # Arrange
        document = {**EMPTY_INBOX, "answers": [{"id": "disk_20261019T090000Z_b2", "study": "disk", "project": None}]}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertIn(
            '<section><h2>Study answers</h2><ul><li><a href="#inbox/disk_20261019T090000Z_b2">'
            "disk_20261019T090000Z_b2</a> disk -</li></ul></section>",
            fragment,
        )


class RenderInboxViewOfStringsHoldingMarkupTest(unittest.TestCase):
    def test_should_leave_none_of_the_markup_in_the_fragment(self):
        # Arrange
        markup = '<img src=x onerror="alert(1)">'
        document = {
            "schema_version": 1,
            "signals": [
                {
                    "id": markup,
                    "fingerprint": markup,
                    "kind": markup,
                    "project": markup,
                    "count": 1,
                    "age_s": 60,
                    "status": "new",
                    "stale": False,
                }
            ],
            "families": [{"by": markup, "key": markup, "signals": [markup]}],
            "patterns": [
                {
                    "name": markup,
                    "title": markup,
                    "action": "order",
                    "target": markup,
                    "recipe": markup,
                    "repeats": None,
                    "signals": [],
                },
                {
                    "name": "other",
                    "title": "t",
                    "action": None,
                    "target": None,
                    "recipe": None,
                    "repeats": markup,
                    "signals": [],
                },
            ],
            "answers": [{"id": markup, "study": markup, "project": markup}],
        }

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertNotIn("<img", fragment)
        self.assertNotIn('"alert', fragment)
