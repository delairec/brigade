import unittest

from brigade.dashboard.render_needs_you_row import NeedsYou, render_needs_you_row


class RenderNeedsYouRowTest(unittest.TestCase):
    def test_should_name_what_waits_why_and_the_command_to_copy_escaped(self):
        # Arrange
        row = NeedsYou(subject="B7 <x>", reason="parked on 'q'", command="brigade wave requeue w1 B7 && ls")

        # Act
        rendered = render_needs_you_row(row)

        # Assert
        self.assertEqual(
            rendered,
            '<li class="needs-you"><span class="needs-you-subject">B7 &lt;x&gt;</span>'
            '<span class="needs-you-reason">parked on &#x27;q&#x27;</span>'
            '<code class="needs-you-action">brigade wave requeue w1 B7 &amp;&amp; ls</code></li>',
        )
