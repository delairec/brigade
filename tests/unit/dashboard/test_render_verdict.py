import unittest

from brigade.dashboard.render_verdict import Verdict, VerdictLink, render_verdict


class RenderVerdictTest(unittest.TestCase):
    def test_should_frame_the_sentence_and_what_explains_it_in_the_tone_of_the_state(self):
        # Arrange
        verdict = Verdict(sentence="Brigade is idle <now>.", explanation=("No wave & no run.",), state="parked")

        # Act
        rendered = render_verdict(verdict)

        # Assert
        self.assertEqual(
            rendered,
            '<div class="verdict tone-you"><p class="status-sentence">Brigade is idle &lt;now&gt;.</p>'
            "<p>No wave &amp; no run.</p></div>",
        )

    def test_should_leave_out_the_explanation_when_there_is_none(self):
        # Arrange
        no_explanation = ()
        verdict = Verdict(sentence="Brigade is working.", explanation=no_explanation, state="running")

        # Act
        rendered = render_verdict(verdict)

        # Assert
        self.assertEqual(
            rendered, '<div class="verdict tone-work"><p class="status-sentence">Brigade is working.</p></div>'
        )

    def test_should_link_a_part_of_the_explanation_escaping_its_label_and_its_address(self):
        # Arrange
        explanation = ("The last wave, ", VerdictLink(label="w<1>", address="#waves/w&1"), ", closed & merged.")
        verdict = Verdict(sentence="Brigade is idle.", explanation=explanation, state="idle")

        # Act
        rendered = render_verdict(verdict)

        # Assert
        self.assertIn(
            '<p>The last wave, <a class="mono" href="#waves/w&amp;1">w&lt;1&gt;</a>, closed &amp; merged.</p>', rendered
        )
