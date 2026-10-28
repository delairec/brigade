import unittest

from brigade.dashboard.render_inbox_view import render_inbox_view

NOTE_ID = "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc"
THREAD_ID = "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f"


class RenderInboxViewTest(unittest.TestCase):
    def test_should_show_the_signals_by_family_and_the_proposed_patterns_with_their_actions(self):
        # Arrange
        document = {
            "schema_version": 1,
            "signals": [
                {
                    "id": NOTE_ID,
                    "fingerprint": "note:474fa40ae4db",
                    "kind": "note",
                    "project": "oak",
                    "count": 1,
                    "age_s": 172800,
                    "status": "new",
                },
                {
                    "id": THREAD_ID,
                    "fingerprint": "rt:PRRT_kwDO",
                    "kind": "review_thread",
                    "project": None,
                    "count": 3,
                    "age_s": 3600,
                    "status": "new",
                },
            ],
            "families": [
                {"by": "file", "key": "brigade/cli.py", "signals": [NOTE_ID, THREAD_ID]},
                {"by": "signal", "key": "rt:PRRT_kwDO", "signals": [THREAD_ID]},
            ],
            "patterns": [
                {"name": "FlakyTests", "action": "constraint", "signals": [NOTE_ID]},
                {"name": "LongNames", "action": None, "signals": []},
            ],
        }

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertEqual(
            fragment,
            "<section><h2>Signals</h2>"
            "<section><h3>file brigade/cli.py</h3><ul>"
            f'<li><code>a4a5f46</code> note oak, 1 in 2d <button data-post="/api/inbox/dismiss/{NOTE_ID}">'
            "dismiss</button></li>"
            f'<li><code>19757dd</code> review_thread -, 3 in 1h <button data-post="/api/inbox/dismiss/{THREAD_ID}">'
            "dismiss</button></li>"
            "</ul></section>"
            "<section><h3>signal rt:PRRT_kwDO</h3><ul>"
            f'<li><code>19757dd</code> review_thread -, 3 in 1h <button data-post="/api/inbox/dismiss/{THREAD_ID}">'
            "dismiss</button></li>"
            "</ul></section>"
            "</section>"
            "<section><h2>Patterns</h2>"
            "<article><h3>FlakyTests</h3><p>constraint</p><ul><li><code>a4a5f46</code></li></ul>"
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=rule">ratify as rule</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=guard">ratify as guard</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=lint">ratify as lint</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=schema">ratify as schema</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=skill">ratify as skill</button>'
            '<button data-post="/api/inbox/ratify/FlakyTests?kind=script">ratify as script</button>'
            '<button data-post="/api/inbox/dismiss/FlakyTests">dismiss</button></article>'
            "<article><h3>LongNames</h3><p>-</p><ul></ul>"
            '<button data-post="/api/inbox/ratify/LongNames">ratify</button>'
            '<button data-post="/api/inbox/dismiss/LongNames">dismiss</button></article>'
            "</section>",
        )

    def test_should_say_the_inbox_holds_no_new_signal_and_no_proposed_pattern(self):
        # Arrange
        document = {"schema_version": 1, "signals": [], "families": [], "patterns": []}

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertEqual(
            fragment,
            "<section><h2>Signals</h2><p>no new signal</p></section>"
            "<section><h2>Patterns</h2><p>no pattern proposed</p></section>",
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
                }
            ],
            "families": [{"by": markup, "key": markup, "signals": [markup]}],
            "patterns": [{"name": markup, "action": markup, "signals": [markup]}],
        }

        # Act
        fragment = render_inbox_view(document)

        # Assert
        self.assertNotIn("<img", fragment)
        self.assertNotIn('"alert', fragment)
