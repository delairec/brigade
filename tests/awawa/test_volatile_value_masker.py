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
