import unittest

from brigade.tick.forge_login_keeper import ForgeLoginKeeper

TOKEN_OF_THE_CLI = {"schema_version": 1, "environment": {"GH_TOKEN": "t0k3n"}}
NO_TOKEN = {"schema_version": 1, "environment": None}
LOGIN_OF_THE_CLI = {"schema_version": 1, "login": "tidepool-cli"}
LOGIN_OF_THE_BUILD = {"schema_version": 1, "login": "tidepool-build"}
NO_RUNTIME = None


class LoginForgeDouble:
    def __init__(self, answers: list[dict]):
        self.answers = answers
        self.requests = []

    def read_login_environment(self, request: dict, runtime) -> dict:
        self.requests.append(request)
        return self.answers[len(self.requests) - 1]

    def merge_pull_request(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "merged": request["number"]}


class ForgeLoginKeeperTest(unittest.TestCase):
    def test_should_ask_the_forge_once_for_the_environment_of_a_login(self):
        # Arrange
        forge = LoginForgeDouble([TOKEN_OF_THE_CLI])
        keeper = ForgeLoginKeeper(forge)
        keeper.read_login_environment(LOGIN_OF_THE_CLI, NO_RUNTIME)

        # Act
        keeper.read_login_environment(LOGIN_OF_THE_CLI, NO_RUNTIME)

        # Assert
        self.assertEqual(forge.requests, [{"schema_version": 1, "login": "tidepool-cli"}])

    def test_should_answer_the_environment_kept_for_a_login(self):
        # Arrange
        keeper = ForgeLoginKeeper(LoginForgeDouble([TOKEN_OF_THE_CLI]))
        keeper.read_login_environment(LOGIN_OF_THE_CLI, NO_RUNTIME)

        # Act
        environment = keeper.read_login_environment(LOGIN_OF_THE_CLI, NO_RUNTIME)

        # Assert
        self.assertEqual(environment, {"schema_version": 1, "environment": {"GH_TOKEN": "t0k3n"}})

    def test_should_ask_the_forge_for_each_login_apart(self):
        # Arrange
        forge = LoginForgeDouble([TOKEN_OF_THE_CLI, NO_TOKEN])
        keeper = ForgeLoginKeeper(forge)
        keeper.read_login_environment(LOGIN_OF_THE_CLI, NO_RUNTIME)

        # Act
        environment = keeper.read_login_environment(LOGIN_OF_THE_BUILD, NO_RUNTIME)

        # Assert
        self.assertEqual(environment, {"schema_version": 1, "environment": None})

    def test_should_ask_the_forge_again_for_a_login_that_had_no_token(self):
        # Arrange
        forge = LoginForgeDouble([NO_TOKEN, TOKEN_OF_THE_CLI])
        keeper = ForgeLoginKeeper(forge)
        keeper.read_login_environment(LOGIN_OF_THE_CLI, NO_RUNTIME)

        # Act
        environment = keeper.read_login_environment(LOGIN_OF_THE_CLI, NO_RUNTIME)

        # Assert
        self.assertEqual(environment, {"schema_version": 1, "environment": {"GH_TOKEN": "t0k3n"}})

    def test_should_pass_every_other_operation_to_the_forge(self):
        # Arrange
        keeper = ForgeLoginKeeper(LoginForgeDouble([]))

        # Act
        answer = keeper.merge_pull_request({"number": 368}, NO_RUNTIME)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "merged": 368})
