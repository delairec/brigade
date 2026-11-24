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
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><h1>Inbox</h1>'
                '<p class="lede">What brigade noticed and could not settle alone.'
                " You decide: turn a finding into work, or dismiss it.</p></div>"
                '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>'
                '<div class="verdict"><p class="status-sentence">2 proposed patterns to decide first,'
                " then 2 new signals and 1 study answers to read.</p></div>"
                '<div class="stat-tiles">'
                '<div class="stat-tile"><span class="stat-value">2</span>'
                '<span class="stat-label">patterns to decide</span>'
                '<span class="stat-perimeter">1 finding, 1 repeat</span></div>'
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
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Decide first</h2>'
            "<p>The patterns that still hold new signals, the most covered first.</p></div>"
            '<ul class="panel todo"><li class="needs-you tone-you"><span class="mark">1\u00d7</span>'
            "<div><h3>the title of FlakyTests</h3>"
            '<p class="pattern-name"><a href="#inbox/FlakyTests"><code>FlakyTests</code></a>'
            " · cites 1 signal, new</p>"
            "<p>If ratified: a request on oak, planned into a wave</p></div>"
            '<div class="act"><button class="btn btn-primary" type="button" data-post="/api/inbox/ratify/FlakyTests">'
            'Ratify</button><button class="btn" type="button" data-post="/api/inbox/dismiss/FlakyTests">Dismiss</button>'
            "</div></li></ul></section>",
            fragment,
        )

    def test_should_count_the_signals_it_cites_and_those_of_them_still_new(self):
        # Arrange
        document = {
            **EMPTY_INBOX,
            "signals": [NOTE],
            "patterns": [create_pattern("FlakyTests", None, [NOTE_ID, DISMISSED_ID])],
        }

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn("<code>FlakyTests</code></a> · cites 2 signals, 1 of them new</p>", fragment)

    def test_should_count_the_times_a_pattern_was_proposed_once_a_repeat_proposed_it_again(self):
        # Arrange
        pattern = create_pattern("Flaky", None, [NOTE_ID])
        repeat = create_pattern("FlakyAgain", "Flaky", [NOTE_ID])
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [pattern, repeat]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            "<code>Flaky</code></a> · proposed 2 times, 1 of them while the first was still undecided"
            " · cites 1 signal, new</p>",
            fragment,
        )

    def test_should_say_ratifying_starts_nothing_until_a_pattern_acting_on_a_target_names_one(self):
        for action in ("wave", "constraint", "order"):
            with self.subTest(action=action):
                # Arrange
                pattern = {**create_pattern("FlakyTests", None, [NOTE_ID]), "action": action, "target": None}
                document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [pattern]}

                # Act
                fragment = render_inbox_view(document, {})

                # Assert
                self.assertIn("<p>If ratified: nothing until the pattern names a target</p>", fragment)

    def test_should_say_ratifying_an_order_starts_nothing_until_the_pattern_names_a_recipe(self):
        # Arrange
        pattern = {**create_pattern("StaleLocks", None, [NOTE_ID]), "action": "order", "recipe": None}
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [pattern]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn("<p>If ratified: nothing until the pattern names a recipe</p>", fragment)

    def test_should_say_ratifying_an_order_starts_an_order_of_the_recipe_it_names(self):
        # Arrange
        pattern = {**create_pattern("StaleLocks", None, [NOTE_ID]), "action": "order", "recipe": "clear-locks"}
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [pattern]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn("<p>If ratified: an order of the recipe clear-locks on oak</p>", fragment)

    def test_should_fold_two_repeats_under_the_pattern_they_name_each_with_its_buttons(self):
        # Arrange
        document = {
            **EMPTY_INBOX,
            "signals": [NOTE],
            "patterns": [
                create_pattern("FlakyTests", None, [NOTE_ID]),
                create_pattern("FlakyTestsAgain", "FlakyTests", [NOTE_ID]),
                create_pattern("FlakyTestsOnceMore", "FlakyTests", [NOTE_ID]),
            ],
        }

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            "<p>If ratified: a request on oak, planned into a wave</p>"
            '<details class="fold"><summary>2 repeats</summary><ul class="repeats">'
            '<li><a href="#inbox/FlakyTestsAgain"><code>FlakyTestsAgain</code></a> the title of FlakyTestsAgain'
            '<span class="act"><button class="btn" type="button" data-post="/api/inbox/ratify/FlakyTestsAgain">'
            'Ratify</button><button class="btn" type="button" data-post="/api/inbox/dismiss/FlakyTestsAgain">'
            "Dismiss</button></span></li>"
            '<li><a href="#inbox/FlakyTestsOnceMore"><code>FlakyTestsOnceMore</code></a>'
            " the title of FlakyTestsOnceMore"
            '<span class="act"><button class="btn" type="button" data-post="/api/inbox/ratify/FlakyTestsOnceMore">'
            'Ratify</button><button class="btn" type="button" data-post="/api/inbox/dismiss/FlakyTestsOnceMore">'
            "Dismiss</button></span></li></ul></details></div>",
            fragment,
        )

    def test_should_fold_a_single_repeat_under_a_summary_in_the_singular(self):
        # Arrange
        document = {
            **EMPTY_INBOX,
            "signals": [NOTE],
            "patterns": [
                create_pattern("FlakyTests", None, [NOTE_ID]),
                create_pattern("FlakyTestsAgain", "FlakyTests", [NOTE_ID]),
            ],
        }

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn('<details class="fold"><summary>1 repeat</summary>', fragment)

    def test_should_let_a_repeat_of_a_pattern_no_longer_proposed_stand_alone_naming_what_it_repeats(self):
        # Arrange
        document = {
            **EMPTY_INBOX,
            "signals": [NOTE],
            "patterns": [create_pattern("FlakyTestsAgain", "FlakyTests", [NOTE_ID])],
        }

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Decide first</h2>'
            "<p>The patterns that still hold new signals, the most covered first.</p></div>"
            '<ul class="panel todo"><li class="needs-you tone-you"><span class="mark">1\u00d7</span>'
            "<div><h3>the title of FlakyTestsAgain</h3>"
            '<p class="pattern-name"><a href="#inbox/FlakyTestsAgain"><code>FlakyTestsAgain</code></a>'
            " repeats <code>FlakyTests</code> · cites 1 signal, new</p>",
            fragment,
        )

    def test_should_group_the_new_signals_by_what_recorded_them_the_uncovered_first_naming_each_subject(self):
        # Arrange
        scan = {
            **NOTE,
            "id": DISMISSED_ID,
            "kind": "scan",
            "fingerprint": "stale_branches_oak:oak:fix/tests-ledger",
            "count": 3,
            "age_s": 1468800,
        }
        document = {
            **EMPTY_INBOX,
            "signals": [scan, NOTE],
            "patterns": [create_pattern("BranchesLeftBehind", None, [DISMISSED_ID])],
        }

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>New signals</h2>'
            "<p>2 signals, by what recorded them.</p></div>"
            '<details class="fold" open><summary>Notes <span>· 1 signal · oldest 2d · not covered by any pattern</span>'
            '</summary><div class="panel scroll"><table><thead><tr><th>Signal</th><th>What</th><th class="num">Seen</th>'
            '<th class="num">First seen</th><th></th></tr></thead><tbody>'
            f'<tr><td class="mono"><a href="#inbox/{NOTE_ID}">a4a5f46</a></td><td>oak</td><td class="num">once</td>'
            f'<td class="num">2d ago</td><td class="num"><button class="btn" type="button"'
            f' data-post="/api/inbox/dismiss/{NOTE_ID}">Dismiss</button></td></tr>'
            "</tbody></table></div></details>"
            '<details class="fold"><summary>Scan stale_branches_oak <span>· 1 signal · oldest 17d · all covered by a'
            ' pattern</span></summary><div class="panel scroll"><table><thead><tr><th>Signal</th><th>What</th>'
            '<th class="num">Seen</th><th class="num">First seen</th><th></th></tr></thead><tbody>'
            f'<tr><td class="mono"><a href="#inbox/{DISMISSED_ID}">0d1e2f3</a></td><td>fix/tests-ledger</td>'
            f'<td class="num">3 times</td><td class="num">17d ago</td><td class="num"><button class="btn" type="button"'
            f' data-post="/api/inbox/dismiss/{DISMISSED_ID}">Dismiss</button></td></tr>'
            "</tbody></table></div></details></section>",
            fragment,
        )

    def test_should_count_the_signals_of_a_group_a_pattern_covers_when_it_covers_some(self):
        # Arrange
        other_note = {**NOTE, "id": DISMISSED_ID}
        document = {
            **EMPTY_INBOX,
            "signals": [NOTE, other_note],
            "patterns": [create_pattern("Noted", None, [NOTE_ID])],
        }

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            "<summary>Notes <span>· 2 signals · oldest 2d · 1 of 2 covered by a pattern</span></summary>", fragment
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
            "last_action": "2026-10-19T05:00:00Z",
        }
        document = {**EMPTY_INBOX, "signals": [stall]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            f'<a href="#inbox/{STALL_ID}">5c1e0d9</a></td><td>B17 of <a class="mono" href="#waves/oak_w2">oak_w2</a>'
            ' · last action 05:00:00Z <span class="stale">stale: its task merged since</span></td>',
            fragment,
        )

    def test_should_say_why_each_region_is_empty(self):
        # Act
        fragment = render_inbox_view(EMPTY_INBOX, {})

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Decide first</h2>'
            "<p>The patterns that still hold new signals, the most covered first.</p></div>"
            '<div class="empty-state"><p class="empty-why">no pattern waits for a decision</p>'
            '<p class="empty-fill">the daily triage proposes one from the new signals</p></div></section>'
            '<section class="block"><div class="block-head"><h2>New signals</h2></div>'
            '<div class="empty-state"><p class="empty-why">no new signal is in the inbox</p>'
            '<p class="empty-fill">a review thread, a stall, a check run, a note or a scan records one</p></div>'
            "</section>"
            '<section class="block"><div class="block-head"><h2>Study answers</h2></div>'
            '<div class="empty-state"><p class="empty-why">no study answer is to read</p>'
            '<p class="empty-fill">a study run writes one</p></div></section>',
            fragment,
        )

    def test_should_link_each_study_answer_to_its_view(self):
        # Arrange
        document = {**EMPTY_INBOX, "answers": [{"id": "disk_20261019T090000Z_b2", "study": "disk", "project": None}]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Study answers</h2></div><ul><li><a href="#inbox/disk_20261019T090000Z_b2">'
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
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertNotIn("<img", fragment)
        self.assertNotIn('"alert', fragment)


class RenderInboxViewHeadTest(unittest.TestCase):
    def test_should_open_on_the_page_head_naming_the_view_and_what_it_is_for(self):
        # Act
        fragment = render_inbox_view(EMPTY_INBOX, {})

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><h1>Inbox</h1>'
                '<p class="lede">What brigade noticed and could not settle alone. You decide: turn a finding into work, or dismiss it.</p></div>'
                '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>'
            ),
            fragment[:300],
        )


class RenderInboxViewAsTheMockupTest(unittest.TestCase):
    def test_should_say_how_to_read_the_page_in_an_explainer(self):
        # Act
        fragment = render_inbox_view(EMPTY_INBOX, {})

        # Assert
        self.assertIn('<details class="explainer"><summary>How to read this page</summary>', fragment)

    def test_should_lay_a_pattern_to_decide_as_a_row_counting_its_proposals_with_ratify_first_at_its_right(self):
        # Arrange
        pattern = create_pattern("Flaky", None, [NOTE_ID])
        repeat = create_pattern("FlakyAgain", "Flaky", [NOTE_ID])
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [pattern, repeat]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            '<ul class="panel todo"><li class="needs-you tone-you"><span class="mark">2\u00d7</span>', fragment
        )
        self.assertIn(
            '<div class="act"><button class="btn btn-primary" type="button" data-post="/api/inbox/ratify/Flaky">'
            'Ratify</button><button class="btn" type="button" data-post="/api/inbox/dismiss-all/Flaky">'
            "Dismiss all 2</button></div>",
            fragment,
        )

    def test_should_give_each_kind_of_a_constraint_the_address_choosing_it_leads_to_and_ratify_the_kind_chosen(self):
        # Arrange
        pattern = {**create_pattern("FlakyTests", None, [NOTE_ID]), "action": "constraint"}
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [pattern]}

        # Act
        fragment = render_inbox_view(document, {"FlakyTests": "lint"})

        # Assert
        self.assertIn(
            '<span class="field"><label for="kind-FlakyTests">as</label><select id="kind-FlakyTests" name="kind">'
            '<option value="rule" data-href="inbox?kind-FlakyTests=rule">rule</option>'
            '<option value="guard" data-href="inbox?kind-FlakyTests=guard">guard</option>'
            '<option value="lint" data-href="inbox?kind-FlakyTests=lint" selected>lint</option>',
            fragment,
        )
        self.assertIn(
            '<button class="btn btn-primary" type="button" data-post="/api/inbox/ratify/FlakyTests?kind=lint">'
            "Ratify</button>",
            fragment,
        )

    def test_should_ratify_a_constraint_as_a_rule_until_another_kind_is_chosen(self):
        # Arrange
        pattern = {**create_pattern("FlakyTests", None, [NOTE_ID]), "action": "constraint"}
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [pattern]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn('data-post="/api/inbox/ratify/FlakyTests?kind=rule">Ratify</button>', fragment)

    def test_should_set_aside_in_a_table_the_patterns_whose_signals_are_no_longer_new(self):
        # Arrange
        no_cited_signal = []
        settled = create_pattern("Settled", None, [DISMISSED_ID])
        silent = create_pattern("Silent", None, no_cited_signal)
        live = create_pattern("Live", None, [NOTE_ID])
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [settled, silent, live]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        other = fragment.index("<h2>Other proposals</h2>")
        self.assertLess(fragment.index("the title of Live"), other)
        self.assertGreater(fragment.index("the title of Settled"), other)
        self.assertGreater(fragment.index("the title of Silent"), other)
        self.assertIn(
            "<h2>Other proposals</h2><p>2 patterns whose signals are all dismissed, or that cite none.</p>", fragment
        )
        self.assertIn(
            '<thead><tr><th>Finding</th><th class="num">Proposed</th><th>Action</th><th class="num">Signals cited</th>'
            "<th></th></tr></thead>",
            fragment,
        )

    def test_should_put_first_the_pattern_holding_the_most_new_signals(self):
        # Arrange
        thin = create_pattern("Thin", None, [NOTE_ID])
        wide = create_pattern("Wide", None, [NOTE_ID, THREAD_ID])
        document = {**EMPTY_INBOX, "signals": [NOTE, THREAD], "patterns": [thin, wide]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertLess(fragment.index("the title of Wide"), fragment.index("the title of Thin"))

    def test_should_set_aside_a_pattern_citing_no_signal_among_the_other_proposals(self):
        # Arrange
        no_cited_signal = []
        silent = create_pattern("Silent", None, no_cited_signal)
        document = {**EMPTY_INBOX, "signals": [NOTE], "patterns": [silent]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn(
            "<h2>Other proposals</h2><p>1 pattern whose signals are all dismissed, or that cite none.</p>", fragment
        )
        self.assertGreater(fragment.index("the title of Silent"), fragment.index("<h2>Other proposals</h2>"))

    def test_should_fold_the_new_signals_of_each_kind_in_a_table(self):
        # Arrange
        document = {**EMPTY_INBOX, "signals": [NOTE]}

        # Act
        fragment = render_inbox_view(document, {})

        # Assert
        self.assertIn('<details class="fold" open><summary>Notes <span>· 1 signal', fragment)
        self.assertIn(
            '<thead><tr><th>Signal</th><th>What</th><th class="num">Seen</th><th class="num">First seen</th><th></th>'
            "</tr></thead>",
            fragment,
        )
