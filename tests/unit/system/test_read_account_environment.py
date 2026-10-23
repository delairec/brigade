import unittest

from brigade.system.parse_configuration import Configuration
from brigade.system.read_account_environment import ForgeAccount, read_account_environment

NO_RUNTIME_NEEDED = None


class ForgeHandingATokenDouble:
    def __init__(self):
        self.logins = []

    def read_login_environment(self, request: dict, runtime) -> dict:
        self.logins.append(request["login"])
        return {"schema_version": 1, "environment": {"GH_TOKEN": "token-of-octo-builder"}}


class ReadAccountEnvironmentTest(unittest.TestCase):
    def test_should_answer_the_environment_of_the_login_bound_to_the_key(self):
        # Arrange
        forge = ForgeHandingATokenDouble()
        configuration = Configuration(forge_accounts={"build": "octo-builder"})

        # Act
        environment = read_account_environment(
            ForgeAccount(forge=forge, forge_name="github", key="build"), configuration, NO_RUNTIME_NEEDED
        )

        # Assert
        self.assertEqual(environment, {"GH_TOKEN": "token-of-octo-builder"})
        self.assertEqual(forge.logins, ["octo-builder"])

    def test_should_answer_no_variable_for_a_key_bound_to_no_login(self):
        # Act
        environment = read_account_environment(
            ForgeAccount(forge=None, forge_name="github", key="build"), Configuration(), NO_RUNTIME_NEEDED
        )

        # Assert
        self.assertEqual(environment, {})
