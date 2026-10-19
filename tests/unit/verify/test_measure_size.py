import unittest

from brigade.git.count_changed_lines import ChangedFile
from brigade.verify.measure_size import measure_size


class MeasureSizeTest(unittest.TestCase):
    def test_should_count_the_files_lines_packages_and_layers_changed(self):
        # Arrange
        changed = (
            ChangedFile(path="shop/domain/cart.py", insertions=10, deletions=2),
            ChangedFile(path="shop/domain/order.py", insertions=1, deletions=0),
            ChangedFile(path="docs/cart.md", insertions=2, deletions=0),
        )

        # Act
        size = measure_size(changed)

        # Assert
        self.assertEqual(
            size,
            {
                "name": "size",
                "verdict": "info",
                "findings": ["3 files", "15 lines", "2 packages: docs, shop/domain", "1 layers: domain"],
            },
        )

    def test_should_count_nothing_for_no_change(self):
        # Arrange
        no_change = ()

        # Act
        size = measure_size(no_change)

        # Assert
        self.assertEqual(size["findings"], ["0 files", "0 lines", "0 packages", "0 layers"])
