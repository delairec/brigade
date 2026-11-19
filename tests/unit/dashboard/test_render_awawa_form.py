import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_form import AwawaForm, render_awawa_form

FILTERED_BOARD = AwawaAddress(
    project="my oak",
    parameters=(("view", "board"), ("filter", "STATUS=todo"), ("filter", "ROLE=ada"), ("search", "read")),
)


class RenderAwawaFormTest(unittest.TestCase):
    def test_should_carry_the_address_but_the_parameters_its_controls_replace_and_post_nothing(self):
        # Arrange
        form = AwawaForm(
            css_class="awawa-search",
            address=FILTERED_BOARD,
            controls='<input name="search">',
            replaced=("search",),
            button="Apply",
        )

        # Act
        fragment = render_awawa_form(form)

        # Assert
        self.assertEqual(
            fragment,
            '<form class="awawa-search" method="get" data-view="awawa/my%20oak">'
            '<input type="hidden" name="view" value="board">'
            '<input type="hidden" name="filter" value="STATUS=todo">'
            '<input type="hidden" name="filter" value="ROLE=ada">'
            '<input name="search"><button>Apply</button></form>',
        )

    def test_should_escape_a_parameter_holding_markup(self):
        # Arrange
        form = AwawaForm(
            css_class="awawa-search",
            address=AwawaAddress(project="oak", parameters=(("search", '"><b>'),)),
            controls="",
            replaced=(),
            button="Apply",
        )

        # Act
        fragment = render_awawa_form(form)

        # Assert
        self.assertIn('<input type="hidden" name="search" value="&quot;&gt;&lt;b&gt;">', fragment)
