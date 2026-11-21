import unittest

from brigade.dashboard.render_dashboard_page import render_dashboard_page

SHELL = (
    "<head>\n"
    '<meta name="brigade-token" content="">\n'
    '<link rel="stylesheet" href="/dashboard.css">\n'
    '<script src="/dashboard.js" defer></script>\n'
    "</head>\n"
    "<body>\n"
    '<div class="heartbeat-region" data-region="/views/heartbeat"></div>\n'
    '<main id="view"></main>\n'
    '<section class="next-tick" hidden><h2>Next tick</h2>'
    '<div class="next-tick-decisions" data-next-tick="/views/next-tick"></div></section>\n'
    "</body>\n"
)


class RenderDashboardPageTest(unittest.TestCase):
    def test_should_inline_the_stylesheet_drop_the_script_and_fill_the_view_and_each_region(self):
        # Arrange
        answers = {
            "/": SHELL,
            "/dashboard.css": "body{color:navy}",
            "/views/waves": "<p>the waves</p>",
            "/views/heartbeat": "<p>last tick</p>",
        }

        # Act
        page = render_dashboard_page("waves", "/views/waves", answers.__getitem__)

        # Assert
        self.assertEqual(
            page,
            "<head>\n"
            '<meta name="brigade-token" content="">\n'
            "<style>body{color:navy}</style>\n"
            "\n"
            "</head>\n"
            "<body>\n"
            '<div class="heartbeat-region" data-region="/views/heartbeat"><p>last tick</p></div>\n'
            '<main id="view"><p>the waves</p></main>\n'
            '<section class="next-tick" hidden><h2>Next tick</h2>'
            '<div class="next-tick-decisions" data-next-tick="/views/next-tick"></div></section>\n'
            "</body>\n",
        )

    def test_should_show_the_next_tick_filled_on_the_page_home_as_its_user_meets_it(self):
        # Arrange
        answers = {
            "/": SHELL,
            "/dashboard.css": "",
            "/views/status?project=oak": "<p>the status</p>",
            "/views/heartbeat": "",
            "/views/next-tick": "<p>launch T7</p>",
        }

        # Act
        page = render_dashboard_page("home", "/views/status?project=oak", answers.__getitem__)

        # Assert
        self.assertIn(
            '<section class="next-tick"><h2>Next tick</h2>'
            '<div class="next-tick-decisions" data-next-tick="/views/next-tick"><p>launch T7</p></div></section>',
            page,
        )
