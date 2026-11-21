import unittest

from brigade.captures.describe_captures_section import describe_captures_section

PAGES = [{"page": "home", "delivered": "/c/home-delivered.png", "reference": "/c/home-reference.png"}]
URLS = {
    "/c/home-delivered.png": "https://gist.githubusercontent.com/octo-bot/abc/raw/home-delivered.png",
    "/c/home-reference.png": "https://gist.githubusercontent.com/octo-bot/abc/raw/home-reference.png",
}


class DescribeCapturesSectionTest(unittest.TestCase):
    def test_should_show_each_page_delivered_beside_its_reference_and_say_the_images_are_public(self):
        # Act
        section = describe_captures_section(PAGES, URLS)

        # Assert
        self.assertEqual(
            section,
            "## Captures\n"
            "\n"
            "Each page the task covers, delivered beside its reference. The images are public, in a gist of the"
            " machine account, as for every pull request the tick opens with captures.\n"
            "\n"
            "| Page | Delivered | Reference |\n"
            "|---|---|---|\n"
            "| home | ![home delivered](https://gist.githubusercontent.com/octo-bot/abc/raw/home-delivered.png)"
            " | ![home reference](https://gist.githubusercontent.com/octo-bot/abc/raw/home-reference.png) |\n",
        )
