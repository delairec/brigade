import os
import unittest
from unittest import mock

from brigade.system.build_process_environment import build_process_environment


class BuildProcessEnvironmentTest(unittest.TestCase):
    def test_should_keep_only_the_whitelisted_variables(self):
        # Arrange
        environment = {
            "PATH": "/usr/bin",
            "HOME": "/home/ada",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "XDG_STATE_HOME": "/home/ada/.local/state",
            "BRIGADE_COLLECTOR": "ci",
            "GH_TOKEN": "secret",
            "SHELL": "/bin/zsh",
        }

        # Act
        with mock.patch.dict(os.environ, environment, clear=True):
            built = build_process_environment()

        # Assert
        self.assertEqual(
            built,
            {
                "PATH": "/usr/bin",
                "HOME": "/home/ada",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "XDG_STATE_HOME": "/home/ada/.local/state",
                "BRIGADE_COLLECTOR": "ci",
            },
        )

    def test_should_pass_on_the_coverage_configuration_of_a_measured_run(self):
        # Arrange
        environment = {"PATH": "/usr/bin", "COVERAGE_PROCESS_CONFIG": "[run]\nsource = brigade\n"}

        # Act
        with mock.patch.dict(os.environ, environment, clear=True):
            built = build_process_environment()

        # Assert
        self.assertEqual(built, {"PATH": "/usr/bin", "COVERAGE_PROCESS_CONFIG": "[run]\nsource = brigade\n"})

    def test_should_pass_on_no_other_coverage_variable(self):
        # Arrange
        environment = {"PATH": "/usr/bin", "COVERAGE_RCFILE": "/home/ada/.coveragerc"}

        # Act
        with mock.patch.dict(os.environ, environment, clear=True):
            built = build_process_environment()

        # Assert
        self.assertEqual(built, {"PATH": "/usr/bin"})
