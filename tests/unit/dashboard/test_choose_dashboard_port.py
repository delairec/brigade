import unittest

from brigade.dashboard.choose_dashboard_port import choose_dashboard_port
from brigade.system.parse_configuration import Configuration

NO_PORT_REQUESTED = None


class ChooseDashboardPortTest(unittest.TestCase):
    def test_should_take_the_port_of_the_option_over_the_configuration(self):
        # Act
        port = choose_dashboard_port(9000, Configuration(dashboard_port=8500))

        # Assert
        self.assertEqual(port, 9000)

    def test_should_take_the_port_of_the_configuration_when_no_option_names_one(self):
        # Act
        port = choose_dashboard_port(NO_PORT_REQUESTED, Configuration(dashboard_port=8500))

        # Assert
        self.assertEqual(port, 8500)

    def test_should_take_the_default_port_when_neither_names_one(self):
        # Act
        port = choose_dashboard_port(NO_PORT_REQUESTED, Configuration())

        # Assert
        self.assertEqual(port, 8470)
