import unittest

from tests.awawa.volatile_value_masker import VolatileValueMasker

TEMPORARY_ROOTS = ["/scratch"]


class VolatileValueMaskerTest(unittest.TestCase):
    def test_should_mask_a_utc_instant_as_a_volatile_value(self):
        # Arrange
        masker = VolatileValueMasker(TEMPORARY_ROOTS)

        # Act
        masked = masker.mask('REQUEST shop_1\n\tCREATED_AT "2026-10-15T08:00:00Z"\n\tPATH "/scratch/shop"\n')

        # Assert
        self.assertEqual(masked, 'REQUEST shop_1\n\tCREATED_AT "<instant:0>"\n\tPATH "<tmp:1>"\n')

    def test_should_unmask_an_instant_to_the_value_it_masked(self):
        # Arrange
        masker = VolatileValueMasker(TEMPORARY_ROOTS)
        masker.mask('CREATED_AT "2026-10-15T08:00:00Z"\n')

        # Act
        unmasked = masker.unmask('CREATED_AT "<instant:0>"\n')

        # Assert
        self.assertEqual(unmasked, 'CREATED_AT "2026-10-15T08:00:00Z"\n')

    def test_should_mask_a_commit_name_as_a_volatile_value(self):
        # Arrange
        masker = VolatileValueMasker(TEMPORARY_ROOTS)

        # Act
        masked = masker.mask("awawa status --json /scratch/refs/shop/518a458e7c6d240131397c4a5003709cdb92b474\n")

        # Assert
        self.assertEqual(masked, "awawa status --json <tmp:0>/shop/<commit:1>\n")

    def test_should_unmask_a_commit_name_to_the_value_it_masked(self):
        # Arrange
        masker = VolatileValueMasker(TEMPORARY_ROOTS)
        masker.mask("518a458e7c6d240131397c4a5003709cdb92b474\n")

        # Act
        unmasked = masker.unmask("<commit:0>\n")

        # Assert
        self.assertEqual(unmasked, "518a458e7c6d240131397c4a5003709cdb92b474\n")

    def test_should_mask_a_run_id_in_either_of_its_forms_as_a_volatile_value(self):
        # Arrange
        masker = VolatileValueMasker(TEMPORARY_ROOTS)

        # Act
        masked = masker.mask('ANSWER trees_20261015T124950Z_05a3de\n\tRUN "20261015T124950Z-05a3de"\n')

        # Assert
        self.assertEqual(masked, 'ANSWER trees_<run_name:0>\n\tRUN "<run:1>"\n')

    def test_should_unmask_a_run_id_to_the_value_it_masked(self):
        # Arrange
        masker = VolatileValueMasker(TEMPORARY_ROOTS)
        masker.mask('ANSWER trees_20261015T124950Z_05a3de\n\tRUN "20261015T124950Z-05a3de"\n')

        # Act
        unmasked = masker.unmask('ANSWER trees_<run_name:0>\n\tRUN "<run:1>"\n')

        # Assert
        self.assertEqual(unmasked, 'ANSWER trees_20261015T124950Z_05a3de\n\tRUN "20261015T124950Z-05a3de"\n')

    def test_should_list_the_run_ids_it_masked_in_the_order_they_sort(self):
        # Arrange
        masker = VolatileValueMasker(TEMPORARY_ROOTS)
        masker.mask(
            'CREATED_AT "2026-10-15T08:00:00Z"\n'
            "ANSWER trees_20261015T124950Z_f00000\n"
            "ANSWER trees_20261015T124950Z_05a3de\n"
        )

        # Act
        ordered = masker.order_run_ids()

        # Assert
        self.assertEqual(ordered, ["<run_name:2>", "<run_name:1>"])
