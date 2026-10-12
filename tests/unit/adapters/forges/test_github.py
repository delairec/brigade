import unittest
from types import SimpleNamespace

from brigade.adapters.forges.github import describe_account, read_login_environment
from brigade.system.run_process import ProcessRecord

UNBOUND_REQUEST = {"schema_version": 1, "environment": {}}
LOGIN_REQUEST = {"schema_version": 1, "login": "octo-bot"}


def create_runtime(stdout: str, exit_code: int = 0) -> SimpleNamespace:
    requests = []

    def run_gh(request):
        requests.append(request)
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr="", duration_ms=0
        )

    return SimpleNamespace(run_process=run_gh, requests=requests)


class DescribeAccountTest(unittest.TestCase):
    def test_should_name_the_active_account_after_an_inactive_one(self):
        # Arrange
        runtime = create_runtime(
            '{"hosts": {"github.com": [{"login": "ada", "active": false}, {"login": "Clauche-bot", "active": true}]}}'
        )

        # Act
        account = describe_account(UNBOUND_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": "Clauche-bot"})

    def test_should_name_no_account_when_none_is_active(self):
        # Arrange
        runtime = create_runtime('{"hosts": {"github.com": [{"login": "ada", "active": false}]}}')

        # Act
        account = describe_account(UNBOUND_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": None})

    def test_should_run_gh_with_the_environment_the_request_carries(self):
        # Arrange
        runtime = create_runtime('{"hosts": {"github.com": [{"login": "octo-bot", "active": true}]}}')
        request = {"schema_version": 1, "environment": {"GH_TOKEN": "token-of-octo-bot"}}

        # Act
        describe_account(request, runtime)

        # Assert
        self.assertEqual(runtime.requests[0].environment, {"GH_TOKEN": "token-of-octo-bot"})


class ReadLoginEnvironmentTest(unittest.TestCase):
    def test_should_answer_the_token_gh_prints_as_gh_token(self):
        # Arrange
        runtime = create_runtime("token-of-octo-bot\n")

        # Act
        answer = read_login_environment(LOGIN_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "environment": {"GH_TOKEN": "token-of-octo-bot"}})

    def test_should_ask_gh_for_the_token_of_the_login_with_no_token_of_its_own(self):
        # Arrange
        runtime = create_runtime("token-of-octo-bot\n")

        # Act
        read_login_environment(LOGIN_REQUEST, runtime)

        # Assert
        self.assertEqual(
            (runtime.requests[0].argv, runtime.requests[0].environment),
            (("gh", "auth", "token", "--hostname", "github.com", "--user", "octo-bot"), {}),
        )

    def test_should_answer_no_environment_when_gh_prints_no_token(self):
        # Arrange
        rows = [
            ("gh refuses the login", "", 1),
            ("gh prints an empty line", "\n", 0),
        ]
        for case, stdout, exit_code in rows:
            with self.subTest(case=case):
                # Arrange
                runtime = create_runtime(stdout, exit_code)

                # Act
                answer = read_login_environment(LOGIN_REQUEST, runtime)

                # Assert
                self.assertEqual(answer, {"schema_version": 1, "environment": None})
