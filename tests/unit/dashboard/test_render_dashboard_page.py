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
        page = render_dashboard_page("waves", answers.__getitem__)

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
            "</body>\n",
        )

    def test_should_show_the_status_view_as_the_page_home(self):
        # Arrange
        answers = {
            "/": SHELL,
            "/dashboard.css": "",
            "/views/status": "<p>the status</p>",
            "/views/heartbeat": "",
        }

        # Act
        page = render_dashboard_page("home", answers.__getitem__)

        # Assert
        self.assertIn('<main id="view"><p>the status</p></main>', page)
