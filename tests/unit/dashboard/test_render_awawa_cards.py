import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_cards import render_awawa_cards
from tests.unit.dashboard.test_render_awawa_card import B1

TREE_OF_OAK = AwawaAddress(project="oak", parameters=(("view", "tree"),))
NO_CARD = []


class RenderAwawaCardsTest(unittest.TestCase):
    def test_should_list_each_card_as_an_item(self):
        # Act
        rendered = render_awawa_cards([B1], TREE_OF_OAK)

        # Assert
        self.assertTrue(rendered.startswith('<ul class="awawa-cards"><li><div class="awawa-card">'), rendered)
        self.assertTrue(rendered.endswith("</div></li></ul>"), rendered)

    def test_should_list_no_item_without_card(self):
        # Act
        rendered = render_awawa_cards(NO_CARD, TREE_OF_OAK)

        # Assert
        self.assertEqual(rendered, '<ul class="awawa-cards"></ul>')
