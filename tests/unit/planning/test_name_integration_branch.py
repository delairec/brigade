import unittest

from brigade.planning.name_integration_branch import name_integration_branch


class NameIntegrationBranchTest(unittest.TestCase):
    def test_should_slug_the_title_of_the_milestone_with_one_hyphen_per_run_of_separators(self):
        for milestone, title, expected_branch in [
            ("W1", "Empty the cart in one click", "integration/W1-empty-the-cart-in-one-click"),
            ("W2", "Pay -- by card, in one click", "integration/W2-pay-by-card-in-one-click"),
            ("W3", "Refund_the  order", "integration/W3-refund-the-order"),
        ]:
            with self.subTest(title=title):
                # Act
                branch = name_integration_branch(milestone, title)

                # Assert
                self.assertEqual(branch, expected_branch)
