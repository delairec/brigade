import unittest

from brigade.dashboard.render_needs_you_row import NeedsYou, render_needs_you_row


class RenderNeedsYouRowTest(unittest.TestCase):
    def test_should_lead_to_the_view_where_the_user_acts_when_the_row_carries_a_link(self):
        # Arrange
        no_command = ""
        row = NeedsYou(
            subject="2 proposed patterns wait for a decision",
            reason="the inbox <proposes> them",
            command=no_command,
            mark="?",
            state="parked",
            link=("Decide in the inbox", "#inbox"),
        )

        # Act
        rendered = render_needs_you_row(row)

        # Assert
        self.assertEqual(
            rendered,
            '<li class="needs-you tone-you"><span class="mark">?</span>'
            "<div><h3>2 proposed patterns wait for a decision</h3><p>the inbox &lt;proposes&gt; them</p></div>"
            '<div class="act"><a class="btn btn-primary" href="#inbox">Decide in the inbox</a></div></li>',
        )

    def test_should_name_what_waits_why_and_the_command_to_copy_escaped(self):
        # Arrange
        row = NeedsYou(
            subject="B7 <x>",
            reason="parked on 'q'",
            command="brigade wave requeue w1 B7 && ls",
            mark="II",
            state="parked",
        )

        # Act
        rendered = render_needs_you_row(row)

        # Assert
        self.assertEqual(
            rendered,
            '<li class="needs-you tone-you"><span class="mark">II</span>'
            "<div><h3>B7 &lt;x&gt;</h3><p>parked on &#x27;q&#x27;</p></div>"
            '<div class="act"><code class="cmd">brigade wave requeue w1 B7 &amp;&amp; ls</code></div></li>',
        )


class RenderNeedsYouRowOfAFaintRowTest(unittest.TestCase):
    def test_should_keep_the_primary_button_for_what_waits_for_the_user_and_a_plain_one_for_a_faint_row(self):
        # Arrange
        faint = NeedsYou("2 stalls merged since", "nothing to do", "", state="queued", link=("Review", "#inbox"))

        # Act
        rendered = render_needs_you_row(faint)

        # Assert
        self.assertIn('<div class="act"><a class="btn" href="#inbox">Review</a></div>', rendered)
