import unittest
from datetime import date
from pathlib import Path

from brigade.collecting.collector_environment import CollectorInputs, create_collector_environment


class CreateCollectorEnvironmentTest(unittest.TestCase):
    def test_should_carry_the_project_the_start_and_the_parameters_as_variables(self):
        # Arrange
        inputs = CollectorInputs(project=Path("/srv/oak"), since=date(2026, 10, 1), parameters={"ref": "v1"})

        # Act
        environment = create_collector_environment(inputs)

        # Assert
        self.assertEqual(
            environment,
            {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": '{"ref": "v1"}'},
        )
