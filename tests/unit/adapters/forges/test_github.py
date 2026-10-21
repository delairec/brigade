import json
import unittest
from types import SimpleNamespace

from brigade.adapters.forges.github import (
    approve_pull_request,
    create_milestone,
    describe_account,
    find_pull_request,
    list_milestones,
    list_pull_requests,
    merge_pull_request,
    open_issue,
    open_pull_request,
    post_review,
    read_login_environment,
    read_pull_request,
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


class DecidePullRequestTest(unittest.TestCase):
    def test_should_ask_gh_to_approve_or_merge_the_pull_request_by_its_method_as_the_login_of_the_environment(self):
        for decide, method, expected_argv in [
            (approve_pull_request, None, ("gh", "pr", "review", "12", "--approve")),
            (merge_pull_request, "squash", ("gh", "pr", "merge", "12", "--squash")),
            (merge_pull_request, "rebase", ("gh", "pr", "merge", "12", "--rebase")),
            (merge_pull_request, "merge", ("gh", "pr", "merge", "12", "--merge")),
        ]:
            with self.subTest(decision=decide.__name__, method=method):
                # Arrange
                runtime = create_runtime("")
                request = {
                    "repository": "/projects/shop",
                    "number": 12,
                    "method": method,
                    "environment": BOT_ENVIRONMENT,
                }

                # Act
                answer = decide(request, runtime)

                # Assert
                [asked] = runtime.requests
                self.assertEqual(
                    (answer, asked.argv, asked.cwd, asked.environment),
                    ({"schema_version": 1}, expected_argv, "/projects/shop", BOT_ENVIRONMENT),
                )


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


class ListPullRequestsTest(unittest.TestCase):
    def test_should_give_the_paginated_read_as_long_as_a_collector(self):
        # Arrange
        no_page = "[]"
        runtime = create_runtime(no_page)

        # Act
        list_pull_requests({"repository": "/projects/shop", "state": "all", "environment": BOT_ENVIRONMENT}, runtime)

        # Assert
        self.assertEqual(runtime.requests[0].timeout_s, 600.0)


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


FIND_REQUEST = {
    "schema_version": 1,
    "repository": "/projects/shop",
    "branch": "task/M1-empty-cart/S3",
    "environment": {"GH_TOKEN": "token-of-octo-cli"},
}
OPEN_PULL_REQUEST = (
    '[{"number": 42, "state": "OPEN", "headRefOid": "0123abc", "baseRefName": "integration/M1-empty-cart",'
    ' "reviewDecision": "CHANGES_REQUESTED", "statusCheckRollup": ['
    '{"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"},'
    '{"__typename": "CheckRun", "name": "lint", "status": "IN_PROGRESS", "conclusion": ""},'
    '{"__typename": "StatusContext", "context": "deploy", "state": "SUCCESS"}]}]'
)
UNREVIEWED_PULL_REQUEST = (
    '[{"number": 42, "state": "MERGED", "headRefOid": "0123abc", "baseRefName": "integration/M1-empty-cart",'
    ' "reviewDecision": "", "statusCheckRollup": []}]'
)


def create_answering_runtime(*stdouts: str) -> SimpleNamespace:
    requests = []

    def run_gh(request):
        requests.append(request)
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=0, stdout=stdouts[len(requests) - 1], stderr="", duration_ms=0
        )

    return SimpleNamespace(run_process=run_gh, requests=requests)


class FindPullRequestTest(unittest.TestCase):
    def test_should_describe_the_pull_request_of_the_branch_with_its_check_runs_its_review_and_its_base(self):
        # Arrange
        runtime = create_answering_runtime(OPEN_PULL_REQUEST, "3\n")

        # Act
        answer = find_pull_request(FIND_REQUEST, runtime)

        # Assert
        self.assertEqual(
            answer,
            {
                "schema_version": 1,
                "pull_request": {
                    "number": 42,
                    "state": "open",
                    "checks": [{"name": "tests", "verdict": "failure"}, {"name": "lint", "verdict": "pending"}],
                    "review": "changes_requested",
                    "behind": True,
                    "head": "0123abc",
                    "base": "integration/M1-empty-cart",
                },
            },
        )

    def test_should_answer_no_review_and_a_base_not_past_the_head(self):
        # Arrange
        runtime = create_answering_runtime(UNREVIEWED_PULL_REQUEST, "0\n")

        # Act
        answer = find_pull_request(FIND_REQUEST, runtime)

        # Assert
        self.assertEqual(
            answer["pull_request"],
            {
                "number": 42,
                "state": "merged",
                "checks": [],
                "review": None,
                "behind": False,
                "head": "0123abc",
                "base": "integration/M1-empty-cart",
            },
        )

    def test_should_answer_no_pull_request_for_a_branch_that_has_none(self):
        # Arrange
        runtime = create_answering_runtime("[]\n")

        # Act
        answer = find_pull_request(FIND_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "pull_request": None})

    def test_should_ask_gh_for_the_newest_pull_request_of_the_branch_then_its_base_as_the_login_of_the_request(self):
        # Arrange
        runtime = create_answering_runtime(OPEN_PULL_REQUEST, "3\n")

        # Act
        find_pull_request(FIND_REQUEST, runtime)

        # Assert
        self.assertEqual(
            [(request.argv, request.cwd, request.environment) for request in runtime.requests],
            [
                (
                    (
                        "gh",
                        "pr",
                        "list",
                        "--head",
                        "task/M1-empty-cart/S3",
                        "--state",
                        "all",
                        "--limit",
                        "1",
                        "--json",
                        "number,state,headRefOid,baseRefName,reviewDecision,statusCheckRollup",
                    ),
                    "/projects/shop",
                    {"GH_TOKEN": "token-of-octo-cli"},
                ),
                (
                    (
                        "gh",
                        "api",
                        "repos/{owner}/{repo}/compare/integration/M1-empty-cart...0123abc",
                        "--jq",
                        ".behind_by",
                    ),
                    "/projects/shop",
                    {"GH_TOKEN": "token-of-octo-cli"},
                ),
            ],
        )


class DescribeAccountOfAnUnreadableHostsDocumentTest(unittest.TestCase):
    def test_should_name_no_account(self):
        # Arrange
        runtime = create_runtime("not a hosts document")

        # Act
        account = describe_account(UNBOUND_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": None})


class OpenIssueTest(unittest.TestCase):
    def test_should_answer_the_url_of_the_issue_opened_without_the_account_environment(self):
        # Arrange
        runtime = create_runtime("https://github.com/ada/shop/issues/7\n")
        request = {"repository": "/projects/shop", "title": "the cart forgets", "body": "Steps\n"}

        # Act
        issue = open_issue(request, runtime)

        # Assert
        self.assertEqual(
            (issue, runtime.requests[0].argv, runtime.requests[0].environment),
            (
                {"schema_version": 1, "url": "https://github.com/ada/shop/issues/7"},
                ("gh", "issue", "create", "--title", "the cart forgets", "--body-file", "-"),
                {},
            ),
        )


LISTED_PAGE = {
    "data": {
        "repository": {
            "pullRequests": {
                "nodes": [
                    {
                        "number": 7,
                        "title": "feat: empty the cart",
                        "headRefName": "task/w1/S3",
                        "baseRefName": "integration/w1",
                        "state": "OPEN",
                        "isDraft": False,
                        "reviewDecision": None,
                        "author": None,
                        "commits": {"nodes": [{"commit": {"statusCheckRollup": None}}]},
                    },
                    {
                        "number": 8,
                        "title": "fix: keep the cart",
                        "headRefName": "task/w1/S4",
                        "baseRefName": "integration/w1",
                        "state": "OPEN",
                        "isDraft": True,
                        "reviewDecision": "APPROVED",
                        "author": {"login": "Clauche-bot"},
                        "commits": {
                            "nodes": [
                                {
                                    "commit": {
                                        "statusCheckRollup": {
                                            "contexts": {
                                                "nodes": [
                                                    {"__typename": "CheckRun", "name": "unit", "conclusion": None},
                                                    {"__typename": "StatusContext"},
                                                ]
                                            }
                                        }
                                    }
                                }
                            ]
                        },
                    },
                ]
            }
        }
    }
}


class ListOpenPullRequestsTest(unittest.TestCase):
    def test_should_describe_each_pull_request_of_the_state_asked(self):
        # Arrange
        runtime = create_runtime(json.dumps([LISTED_PAGE]))

        # Act
        listing = list_pull_requests({**MILESTONES_REQUEST, "state": "open"}, runtime)

        # Assert
        self.assertEqual(
            (listing, runtime.requests[0].argv[9:11]),
            (
                {
                    "schema_version": 1,
                    "pull_requests": [
                        {
                            "number": 7,
                            "title": "feat: empty the cart",
                            "head": "task/w1/S3",
                            "base": "integration/w1",
                            "state": "open",
                            "author": None,
                            "draft": False,
                            "review": None,
                            "checks": [],
                        },
                        {
                            "number": 8,
                            "title": "fix: keep the cart",
                            "head": "task/w1/S4",
                            "base": "integration/w1",
                            "state": "open",
                            "author": "Clauche-bot",
                            "draft": True,
                            "review": "approved",
                            "checks": [{"name": "unit", "verdict": "pending"}],
                        },
                    ],
                },
                ("-f", "states[]=OPEN"),
            ),
        )


class ReadPullRequestTest(unittest.TestCase):
    def test_should_describe_the_pull_request_its_head_and_its_checks(self):
        # Arrange
        runtime = create_runtime(
            json.dumps(
                {
                    "number": 160,
                    "title": "test: cover the rest",
                    "body": "Coverage\n",
                    "headRefName": "test/unit-coverage-rest",
                    "headRefOid": "4f2a9c1",
                    "statusCheckRollup": [{"__typename": "CheckRun", "name": "unit", "conclusion": "SUCCESS"}],
                }
            )
        )

        # Act
        details = read_pull_request({**MILESTONES_REQUEST, "number": 160}, runtime)

        # Assert
        self.assertEqual(
            details,
            {
                "schema_version": 1,
                "pull_request": {
                    "number": 160,
                    "title": "test: cover the rest",
                    "body": "Coverage\n",
                    "head": "test/unit-coverage-rest",
                    "head_sha": "4f2a9c1",
                    "checks": [{"name": "unit", "verdict": "success"}],
                },
            },
        )


class PostReviewTest(unittest.TestCase):
    def test_should_post_the_review_of_the_judged_commit_its_body_on_stdin_under_the_login_of_the_review(self):
        # Arrange
        rows = [("approve", "event=APPROVE"), ("request_changes", "event=REQUEST_CHANGES")]
        for event, expected_field in rows:
            with self.subTest(event=event):
                runtime = create_runtime("")

                # Act
                answer = post_review(
                    {
                        "schema_version": 1,
                        "repository": "/projects/shop",
                        "number": 42,
                        "event": event,
                        "commit": "8885daa",
                        "body": "verdict pass\n",
                        "environment": BOT_ENVIRONMENT,
                    },
                    runtime,
                )

                # Assert
                request = runtime.requests[0]
                self.assertEqual(
                    (answer, request.argv, request.cwd, request.stdin, request.environment),
                    (
                        {"schema_version": 1},
                        (
                            "gh",
                            "api",
                            "repos/{owner}/{repo}/pulls/42/reviews",
                            "--method",
                            "POST",
                            "-f",
                            expected_field,
                            "-f",
                            "commit_id=8885daa",
                            "-F",
                            "body=@-",
                        ),
                        "/projects/shop",
                        "verdict pass\n",
                        {"GH_TOKEN": "token-of-octo-bot"},
                    ),
                )
