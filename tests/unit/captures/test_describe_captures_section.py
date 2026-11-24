import unittest

from brigade.captures.describe_captures_section import describe_captures_section

PAGES = [{"page": "home", "delivered": "/c/home-delivered.png", "reference": "/c/home-reference.png"}]
URLS = {
    "/c/home-delivered.png": "https://gist.githubusercontent.com/octo-bot/abc/raw/home-delivered.png",
    "/c/home-reference.png": "https://gist.githubusercontent.com/octo-bot/abc/raw/home-reference.png",
}
NOT_HOSTED = None


class DescribeCapturesSectionTest(unittest.TestCase):
    def test_should_show_each_page_of_the_head_beside_its_reference_and_say_the_images_are_public(self):
        # Act
        section = describe_captures_section(PAGES, "0123abc", URLS)

        # Assert
        self.assertEqual(
            section,
            "## Captures\n"
            "\n"
            "Each page the task covers at 0123abc, delivered beside its reference. The repository is public: the"
            " images are public too, in a gist of the machine account.\n"
            "\n"
            "| Page | Delivered | Reference |\n"
            "|---|---|---|\n"
            "| home | ![home delivered](https://gist.githubusercontent.com/octo-bot/abc/raw/home-delivered.png)"
            " | ![home reference](https://gist.githubusercontent.com/octo-bot/abc/raw/home-reference.png) |\n",
        )

    def test_should_name_where_the_captures_stay_when_nothing_is_hosted(self):
        # Act
        section = describe_captures_section(PAGES, "0123abc", NOT_HOSTED)

        # Assert
        self.assertEqual(
            section,
            "## Captures\n"
            "\n"
            "Each page the task covers at 0123abc, delivered beside its reference. Nothing is hosted: the repository"
            " is private, or its visibility could not be read. The captures stay in the state directory of the"
            " machine that ran brigade, where the review reads them.\n"
            "\n"
            "| Page | Delivered | Reference |\n"
            "|---|---|---|\n"
            "| home | `/c/home-delivered.png` | `/c/home-reference.png` |\n",
        )
