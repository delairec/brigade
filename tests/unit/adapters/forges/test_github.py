import unittest
from types import SimpleNamespace

from brigade.adapters.forges.github import (
    create_milestone,
    describe_account,
    list_milestones,
    open_pull_request,
    read_login_environment,
)
from brigade.system.run_process import ProcessRecord

UNBOUND_REQUEST = {"schema_version": 1, "environment": {}}
LOGIN_REQUEST = {"schema_version": 1, "login": "octo-bot"}
BOT_ENVIRONMENT = {"GH_TOKEN": "token-of-octo-bot"}
PULL_REQUEST_REQUEST = {
    "repository": "/projects/shop",
    "base": "integration/M1-empty-cart",
    "branch": "task/M1-empty-cart/S3",
    "title": "feat(cart): empty the cart in one click (@TASK.S3)",
    "body": "Empty the cart in one click\n",
    "milestone": "Empty cart",
    "environment": BOT_ENVIRONMENT,
}
MILESTONES_REQUEST = {"repository": "/projects/shop", "environment": BOT_ENVIRONMENT}


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


class OpenPullRequestTest(unittest.TestCase):
    def test_should_answer_the_number_of_the_pull_request_gh_prints_the_address_of(self):
        # Arrange
        runtime = create_runtime("https://github.com/acme/shop/pull/42\n")

        # Act
        answer = open_pull_request(PULL_REQUEST_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "url": "https://github.com/acme/shop/pull/42", "number": 42})

    def test_should_open_it_on_the_base_with_the_milestone_as_the_login_of_the_environment(self):
        # Arrange
        runtime = create_runtime("https://github.com/acme/shop/pull/42\n")

        # Act
        open_pull_request(PULL_REQUEST_REQUEST, runtime)

        # Assert
        self.assertEqual(
            (runtime.requests[0].argv, runtime.requests[0].environment, runtime.requests[0].stdin),
            (
                (
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    "integration/M1-empty-cart",
                    "--head",
                    "task/M1-empty-cart/S3",
                    "--milestone",
                    "Empty cart",
                    "--title",
                    "feat(cart): empty the cart in one click (@TASK.S3)",
                    "--body-file",
                    "-",
                ),
                {"GH_TOKEN": "token-of-octo-bot"},
                "Empty the cart in one click\n",
            ),
        )

    def test_should_open_it_without_a_milestone_when_the_request_names_none(self):
        # Arrange
        runtime = create_runtime("https://github.com/acme/shop/pull/42\n")
        no_milestone = None

        # Act
        open_pull_request({**PULL_REQUEST_REQUEST, "milestone": no_milestone}, runtime)

        # Assert
        self.assertNotIn("--milestone", runtime.requests[0].argv)


class ListMilestonesTest(unittest.TestCase):
    def test_should_answer_the_title_of_every_milestone_of_the_repository_open_or_closed(self):
        # Arrange
        runtime = create_runtime("Empty cart\nWave engine\n")

        # Act
        answer = list_milestones(MILESTONES_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "titles": ["Empty cart", "Wave engine"]})

    def test_should_ask_the_milestones_api_of_the_repository_as_the_login_of_the_environment(self):
        # Arrange
        no_milestone_titles = ""
        runtime = create_runtime(no_milestone_titles)

        # Act
        list_milestones(MILESTONES_REQUEST, runtime)

        # Assert
        self.assertEqual(
            (runtime.requests[0].argv, runtime.requests[0].cwd, runtime.requests[0].environment),
            (
                ("gh", "api", "--paginate", "repos/{owner}/{repo}/milestones?state=all", "--jq", ".[].title"),
                "/projects/shop",
                {"GH_TOKEN": "token-of-octo-bot"},
            ),
        )


class CreateMilestoneTest(unittest.TestCase):
    def test_should_post_the_title_to_the_milestones_api_of_the_repository(self):
        # Arrange
        runtime = create_runtime("{}")

        # Act
        answer = create_milestone({**MILESTONES_REQUEST, "title": "Empty cart"}, runtime)

        # Assert
        self.assertEqual(
            (answer, runtime.requests[0].argv, runtime.requests[0].environment),
            (
                {"schema_version": 1},
                ("gh", "api", "--method", "POST", "repos/{owner}/{repo}/milestones", "-f", "title=Empty cart"),
                {"GH_TOKEN": "token-of-octo-bot"},
            ),
        )
