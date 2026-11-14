import unittest

from brigade.ledger.branch_base_gone import BranchBaseGone


class BranchBaseGoneTest(unittest.TestCase):
    def test_should_read_the_branch_whose_base_is_gone(self):
        # Act
        event = BranchBaseGone.from_document(
            {
                "event": "branch.base_gone",
                "project": "shop",
                "branch": "integration/shop_w3",
                "base": "integration/tides",
            }
        )

        # Assert
        self.assertEqual(event, BranchBaseGone(project="shop", branch="integration/shop_w3", base="integration/tides"))

    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"project": "shop", "branch": "integration/shop_w3", "base": "integration/tides"}

        # Act
        written = BranchBaseGone.from_document(document).to_document()

        # Assert
        self.assertEqual(written, {"project": "shop", "branch": "integration/shop_w3", "base": "integration/tides"})
