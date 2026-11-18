import unittest

from brigade.dashboard.render_status_sentence import render_status_sentence


class RenderStatusSentenceTest(unittest.TestCase):
    def test_should_open_the_page_on_its_sentence_escaped(self):
        # Act
        sentence = render_status_sentence("2 tasks <wait> for you & 1 runs")

        # Assert
        self.assertEqual(sentence, '<p class="status-sentence">2 tasks &lt;wait&gt; for you &amp; 1 runs</p>')
