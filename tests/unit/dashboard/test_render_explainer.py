import unittest

from brigade.dashboard.render_explainer import render_explainer


class RenderExplainerTest(unittest.TestCase):
    def test_should_say_what_the_page_shows_and_what_it_is_for_escaped(self):
        # Act
        rendered = render_explainer("A report <sums up> a wave", "Read it to decide & requeue")

        # Assert
        self.assertEqual(
            rendered,
            '<aside class="explainer"><p class="explainer-what">A report &lt;sums up&gt; a wave</p>'
            '<p class="explainer-use">Read it to decide &amp; requeue</p></aside>',
        )
