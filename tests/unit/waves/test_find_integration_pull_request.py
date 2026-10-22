import unittest

from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.waves.find_integration_pull_request import find_integration_pull_request


class FindIntegrationPullRequestTest(unittest.TestCase):
    def test_should_find_the_pull_request_opened_for_the_wave(self):
        # Arrange
        events = (
            WavePrOpened(wave="shop_w1", pr=77, login="shop-cli"),
            WavePrOpened(wave="shop_w2", pr=81, login="shop-cli"),
            WaveClosed(wave="shop_w1", pr=77),
        )

        # Act
        pull_request = find_integration_pull_request(events, "shop_w1")

        # Assert
        self.assertEqual(pull_request, 77)

    def test_should_find_none_for_a_wave_whose_pull_request_is_not_opened(self):
        # Arrange
        events = (WavePrOpened(wave="shop_w2", pr=81, login="shop-cli"),)

        # Act
        pull_request = find_integration_pull_request(events, "shop_w1")

        # Assert
        self.assertIsNone(pull_request)


if __name__ == "__main__":
    unittest.main()
