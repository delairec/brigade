import json
import unittest

from brigade.adapters.forges.github import (
    BRANCH_CHECK_RUNS_QUERY,
    OPEN_CHECK_RUNS_QUERY,
    PULL_REQUESTS_QUERY,
    REVIEW_THREADS_QUERY,
    THREAD_REPLY_MUTATION,
    approve_pull_request,
    create_milestone,
    describe_account,
    find_pull_request,
    list_check_runs,
    list_milestones,
    list_pull_requests,
    list_review_threads,
    merge_pull_request,
    open_issue,
    open_pull_request,
    post_review,
    read_check_logs,
    read_job_steps,
    read_login_environment,
    read_pull_request,
    reply_review_thread,
    rewrite_pull_request_body,
)
from brigade.errors import CommandFailed
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest
from tests.unit.create_test_runtime import create_test_runtime

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


class GhDouble:
    def __init__(self, answer_request):
        self.answer_request = answer_request
        self.requests = []

    def __call__(self, request: ProcessRequest) -> ProcessRecord:
        self.requests.append(request)
        exit_code, stdout = self.answer_request(request, len(self.requests))
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr="", duration_ms=0
        )


def create_gh(stdout: str, exit_code: int = 0) -> GhDouble:
    return GhDouble(lambda request, rank: (exit_code, stdout))


def create_gh_answering_by_argv(answers: dict) -> GhDouble:
    return GhDouble(lambda request, rank: (0, answers[request.argv]))


def create_gh_answering_in_turn(answers: list[str]) -> GhDouble:
    return GhDouble(lambda request, rank: (0, answers[rank - 1]))


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
                gh = create_gh("")
                runtime = create_test_runtime(run_process=gh)
                request = {
                    "repository": "/projects/shop",
                    "number": 12,
                    "method": method,
                    "environment": BOT_ENVIRONMENT,
                }

                # Act
                answer = decide(request, runtime)

                # Assert
                self.assertEqual(answer, {"schema_version": 1})
                self.assertEqual(
                    gh.requests,
                    [
                        ProcessRequest(
                            argv=expected_argv, cwd="/projects/shop", timeout_s=60.0, environment=BOT_ENVIRONMENT
                        )
                    ],
                )


class RewritePullRequestBodyTest(unittest.TestCase):
    def test_should_ask_gh_to_replace_the_body_of_the_pull_request_as_the_login_of_the_environment(self):
        # Arrange
        gh = create_gh("")
        runtime = create_test_runtime(run_process=gh)
        request = {
            "repository": "/projects/shop",
            "number": 12,
            "body": "# REPORT shop_w1\n",
            "environment": BOT_ENVIRONMENT,
        }

        # Act
        answer = rewrite_pull_request_body(request, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1})
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=("gh", "pr", "edit", "12", "--body-file", "-"),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    stdin="# REPORT shop_w1\n",
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


class DescribeAccountTest(unittest.TestCase):
    def test_should_name_the_active_account_after_an_inactive_one(self):
        # Arrange
        gh = create_gh(
            '{"hosts": {"github.com": [{"login": "ada", "active": false}, {"login": "Clauche-bot", "active": true}]}}'
        )
        runtime = create_test_runtime(run_process=gh)

        # Act
        account = describe_account(UNBOUND_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": "Clauche-bot"})

    def test_should_name_no_account_when_none_is_active(self):
        # Arrange
        gh = create_gh('{"hosts": {"github.com": [{"login": "ada", "active": false}]}}')
        runtime = create_test_runtime(run_process=gh)

        # Act
        account = describe_account(UNBOUND_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": None})

    def test_should_run_gh_with_the_environment_the_request_carries(self):
        # Arrange
        gh = create_gh('{"hosts": {"github.com": [{"login": "octo-bot", "active": true}]}}')
        runtime = create_test_runtime(run_process=gh)
        request = {"schema_version": 1, "environment": {"GH_TOKEN": "token-of-octo-bot"}}

        # Act
        describe_account(request, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=("gh", "auth", "status", "--active", "--hostname", "github.com", "--json", "hosts"),
                    cwd="/",
                    timeout_s=10.0,
                    acceptable_exit_codes=EVERY_EXIT_CODE,
                    stdin=None,
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


class ReadLoginEnvironmentTest(unittest.TestCase):
    def test_should_answer_the_token_gh_prints_as_gh_token(self):
        # Arrange
        gh = create_gh("token-of-octo-bot\n")
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = read_login_environment(LOGIN_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "environment": {"GH_TOKEN": "token-of-octo-bot"}})

    def test_should_ask_gh_for_the_token_of_the_login_with_no_token_of_its_own(self):
        # Arrange
        gh = create_gh("token-of-octo-bot\n")
        runtime = create_test_runtime(run_process=gh)

        # Act
        read_login_environment(LOGIN_REQUEST, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=("gh", "auth", "token", "--hostname", "github.com", "--user", "octo-bot"),
                    cwd="/",
                    timeout_s=10.0,
                    acceptable_exit_codes=EVERY_EXIT_CODE,
                )
            ],
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
                gh = create_gh(stdout, exit_code)
                runtime = create_test_runtime(run_process=gh)

                # Act
                answer = read_login_environment(LOGIN_REQUEST, runtime)

                # Assert
                self.assertEqual(answer, {"schema_version": 1, "environment": None})


class OpenPullRequestTest(unittest.TestCase):
    def test_should_answer_the_number_of_the_pull_request_gh_prints_the_address_of(self):
        # Arrange
        gh = create_gh("https://github.com/acme/shop/pull/42\n")
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = open_pull_request(PULL_REQUEST_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "url": "https://github.com/acme/shop/pull/42", "number": 42})

    def test_should_open_it_on_the_base_with_the_milestone_as_the_login_of_the_environment(self):
        # Arrange
        gh = create_gh("https://github.com/acme/shop/pull/42\n")
        runtime = create_test_runtime(run_process=gh)

        # Act
        open_pull_request(PULL_REQUEST_REQUEST, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
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
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    stdin="Empty the cart in one click\n",
                    environment={"GH_TOKEN": "token-of-octo-bot"},
                )
            ],
        )

    def test_should_open_it_without_a_milestone_when_the_request_names_none(self):
        # Arrange
        gh = create_gh("https://github.com/acme/shop/pull/42\n")
        runtime = create_test_runtime(run_process=gh)
        no_milestone = None

        # Act
        open_pull_request({**PULL_REQUEST_REQUEST, "milestone": no_milestone}, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
                        "gh",
                        "pr",
                        "create",
                        "--base",
                        "integration/M1-empty-cart",
                        "--head",
                        "task/M1-empty-cart/S3",
                        "--title",
                        "feat(cart): empty the cart in one click (@TASK.S3)",
                        "--body-file",
                        "-",
                    ),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    acceptable_exit_codes=(0,),
                    stdin="Empty the cart in one click\n",
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


class ListMilestonesTest(unittest.TestCase):
    def test_should_answer_the_title_of_every_milestone_of_the_repository_open_or_closed(self):
        # Arrange
        gh = create_gh("Empty cart\nWave engine\n")
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = list_milestones(MILESTONES_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "titles": ["Empty cart", "Wave engine"]})

    def test_should_ask_the_milestones_api_of_the_repository_as_the_login_of_the_environment(self):
        # Arrange
        no_milestone_titles = ""
        gh = create_gh(no_milestone_titles)
        runtime = create_test_runtime(run_process=gh)

        # Act
        list_milestones(MILESTONES_REQUEST, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=("gh", "api", "--paginate", "repos/{owner}/{repo}/milestones?state=all", "--jq", ".[].title"),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment={"GH_TOKEN": "token-of-octo-bot"},
                )
            ],
        )


class ListPullRequestsTest(unittest.TestCase):
    def test_should_give_the_paginated_read_as_long_as_a_collector(self):
        # Arrange
        no_page = "[]"
        gh = create_gh(no_page)
        runtime = create_test_runtime(run_process=gh)

        # Act
        list_pull_requests({"repository": "/projects/shop", "state": "all", "environment": BOT_ENVIRONMENT}, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
                        "gh",
                        "api",
                        "graphql",
                        "--paginate",
                        "--slurp",
                        "-F",
                        "owner={owner}",
                        "-F",
                        "name={repo}",
                        "-f",
                        f"query={PULL_REQUESTS_QUERY}",
                    ),
                    cwd="/projects/shop",
                    timeout_s=600.0,
                    acceptable_exit_codes=(0,),
                    stdin=None,
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


class CreateMilestoneTest(unittest.TestCase):
    def test_should_post_the_title_to_the_milestones_api_of_the_repository(self):
        # Arrange
        gh = create_gh("{}")
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = create_milestone({**MILESTONES_REQUEST, "title": "Empty cart"}, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1})
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=("gh", "api", "--method", "POST", "repos/{owner}/{repo}/milestones", "-f", "title=Empty cart"),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment={"GH_TOKEN": "token-of-octo-bot"},
                )
            ],
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


def create_gh_answering(*stdouts: str) -> GhDouble:
    return GhDouble(lambda request, rank: (0, stdouts[rank - 1]))


class FindPullRequestTest(unittest.TestCase):
    def test_should_describe_the_pull_request_of_the_branch_with_its_check_runs_its_review_and_its_base(self):
        # Arrange
        gh = create_gh_answering(OPEN_PULL_REQUEST, "3\n")
        runtime = create_test_runtime(run_process=gh)

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
        gh = create_gh_answering(UNREVIEWED_PULL_REQUEST, "0\n")
        runtime = create_test_runtime(run_process=gh)

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
        gh = create_gh_answering("[]\n")
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = find_pull_request(FIND_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "pull_request": None})

    def test_should_ask_gh_for_the_newest_pull_request_of_the_branch_then_its_base_as_the_login_of_the_request(self):
        # Arrange
        gh = create_gh_answering(OPEN_PULL_REQUEST, "3\n")
        runtime = create_test_runtime(run_process=gh)

        # Act
        find_pull_request(FIND_REQUEST, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
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
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment={"GH_TOKEN": "token-of-octo-cli"},
                ),
                ProcessRequest(
                    argv=(
                        "gh",
                        "api",
                        "repos/{owner}/{repo}/compare/integration/M1-empty-cart...0123abc",
                        "--jq",
                        ".behind_by",
                    ),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment={"GH_TOKEN": "token-of-octo-cli"},
                ),
            ],
        )


class DescribeAccountOfAnUnreadableHostsDocumentTest(unittest.TestCase):
    def test_should_name_no_account(self):
        # Arrange
        gh = create_gh("not a hosts document")
        runtime = create_test_runtime(run_process=gh)

        # Act
        account = describe_account(UNBOUND_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": None})


class OpenIssueTest(unittest.TestCase):
    def test_should_answer_the_url_of_the_issue_opened_under_the_account_environment(self):
        # Arrange
        gh = create_gh("https://github.com/ada/shop/issues/7\n")
        runtime = create_test_runtime(run_process=gh)
        request = {
            "repository": "/projects/shop",
            "title": "the cart forgets",
            "body": "Steps\n",
            "environment": {"GH_TOKEN": "cli-token"},
        }

        # Act
        issue = open_issue(request, runtime)

        # Assert
        self.assertEqual(issue, {"schema_version": 1, "url": "https://github.com/ada/shop/issues/7"})
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=("gh", "issue", "create", "--title", "the cart forgets", "--body-file", "-"),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    stdin="Steps\n",
                    environment={"GH_TOKEN": "cli-token"},
                )
            ],
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


MERGED_PAGE = {
    "data": {
        "repository": {
            "pullRequests": {
                "nodes": [
                    {
                        "number": 5,
                        "title": "docs: the readme",
                        "headRefName": "docs/readme",
                        "baseRefName": "main",
                        "state": "MERGED",
                        "isDraft": False,
                        "reviewDecision": None,
                        "author": {"login": "ada"},
                        "commits": {"nodes": [{"commit": {"statusCheckRollup": None}}]},
                    }
                ]
            }
        }
    }
}


class ListPullRequestsOfEveryStateTest(unittest.TestCase):
    def test_should_ask_the_forge_without_a_state_filter(self):
        # Arrange
        no_page = "[]"
        gh = create_gh(no_page)
        runtime = create_test_runtime(run_process=gh)

        # Act
        list_pull_requests({**MILESTONES_REQUEST, "state": "all"}, runtime)

        # Assert
        self.assertEqual(
            gh.requests[0].argv,
            (
                "gh",
                "api",
                "graphql",
                "--paginate",
                "--slurp",
                "-F",
                "owner={owner}",
                "-F",
                "name={repo}",
                "-f",
                f"query={PULL_REQUESTS_QUERY}",
            ),
        )

    def test_should_present_the_pull_requests_of_every_page_the_forge_answers(self):
        # Arrange
        gh = create_gh(json.dumps([LISTED_PAGE, MERGED_PAGE]))
        runtime = create_test_runtime(run_process=gh)

        # Act
        listing = list_pull_requests({**MILESTONES_REQUEST, "state": "all"}, runtime)

        # Assert
        self.assertEqual(
            listing,
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
                    {
                        "number": 5,
                        "title": "docs: the readme",
                        "head": "docs/readme",
                        "base": "main",
                        "state": "merged",
                        "author": "ada",
                        "draft": False,
                        "review": None,
                        "checks": [],
                    },
                ],
            },
        )


class ListOpenPullRequestsTest(unittest.TestCase):
    def test_should_describe_each_pull_request_of_the_state_asked(self):
        # Arrange
        gh = create_gh(json.dumps([LISTED_PAGE]))
        runtime = create_test_runtime(run_process=gh)

        # Act
        listing = list_pull_requests({**MILESTONES_REQUEST, "state": "open"}, runtime)

        # Assert
        self.assertEqual(
            listing,
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
        )
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
                        "gh",
                        "api",
                        "graphql",
                        "--paginate",
                        "--slurp",
                        "-F",
                        "owner={owner}",
                        "-F",
                        "name={repo}",
                        "-f",
                        "states[]=OPEN",
                        "-f",
                        f"query={PULL_REQUESTS_QUERY}",
                    ),
                    cwd="/projects/shop",
                    timeout_s=600.0,
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


class ReadPullRequestTest(unittest.TestCase):
    def test_should_describe_the_pull_request_its_head_and_its_checks(self):
        # Arrange
        gh = create_gh(
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
        runtime = create_test_runtime(run_process=gh)

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
                gh = create_gh("")
                runtime = create_test_runtime(run_process=gh)

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
                self.assertEqual(answer, {"schema_version": 1})
                self.assertEqual(
                    gh.requests,
                    [
                        ProcessRequest(
                            argv=(
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
                            cwd="/projects/shop",
                            timeout_s=60.0,
                            stdin="verdict pass\n",
                            environment={"GH_TOKEN": "token-of-octo-bot"},
                        )
                    ],
                )


CHECKS_OF_PULL_REQUEST_42 = ("gh", "pr", "checks", "42", "--json", "name,link")
LOGS_OF_JOB_70 = ("gh", "api", "repos/{owner}/{repo}/actions/jobs/70/logs", "--allow-escape-sequences")
JOB_LOGS_REQUEST = ("gh", "api")


def create_gh_unable_to_read_job_logs(answers: dict) -> GhDouble:
    def answer(request: ProcessRequest, rank: int) -> tuple[int, str]:
        if request.argv[:2] != JOB_LOGS_REQUEST:
            return 0, answers[request.argv]
        if 1 not in request.acceptable_exit_codes:
            raise CommandFailed(request.argv, 1, "the response contains terminal escape sequences")
        return 1, ""

    return GhDouble(answer)


class ReadCheckLogsTest(unittest.TestCase):
    def test_should_keep_the_last_lines_of_the_log_of_each_check_asked(self):
        # Arrange
        gh = create_gh_answering_by_argv(
            {
                CHECKS_OF_PULL_REQUEST_42: json.dumps(
                    [
                        {"name": "tests", "link": "https://github.com/octo/shop/actions/runs/7/job/70"},
                        {"name": "lint", "link": "https://github.com/octo/shop/actions/runs/7/job/71"},
                    ]
                ),
                LOGS_OF_JOB_70: "set up\nrun\nFAIL test_cart\nexit 1\n",
            }
        )
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "number": 42,
            "checks": ["tests"],
            "lines": 2,
            "environment": BOT_ENVIRONMENT,
        }

        # Act
        answer = read_check_logs(request, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "logs": [{"name": "tests", "tail": "FAIL test_cart\nexit 1"}]})

    def test_should_mark_unreadable_the_log_of_a_check_gh_cannot_read(self):
        # Arrange
        gh = create_gh_unable_to_read_job_logs(
            {
                CHECKS_OF_PULL_REQUEST_42: json.dumps(
                    [{"name": "tests", "link": "https://github.com/octo/shop/actions/runs/7/job/70"}]
                )
            }
        )
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "number": 42,
            "checks": ["tests"],
            "lines": 2,
            "environment": BOT_ENVIRONMENT,
        }

        # Act
        answer = read_check_logs(request, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "logs": [{"name": "tests", "tail": None, "unreadable": True}]})

    def test_should_hold_no_tail_for_a_check_whose_log_the_forge_does_not_keep(self):
        # Arrange
        gh = create_gh_answering_by_argv(
            {
                CHECKS_OF_PULL_REQUEST_42: json.dumps(
                    [{"name": "coverage", "link": "https://app.codecov.io/gh/octo/shop"}]
                )
            }
        )
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "number": 42,
            "checks": ["coverage"],
            "lines": 2,
            "environment": BOT_ENVIRONMENT,
        }

        # Act
        answer = read_check_logs(request, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "logs": [{"name": "coverage", "tail": None}]})

    def test_should_hold_no_tail_for_a_check_of_another_ci_whose_link_names_a_job(self):
        # Arrange
        gh = create_gh_answering_by_argv(
            {
                CHECKS_OF_PULL_REQUEST_42: json.dumps(
                    [{"name": "jenkins", "link": "https://jenkins.example.com/job/oak/job/main/12/display/redirect"}]
                )
            }
        )
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "number": 42,
            "checks": ["jenkins"],
            "lines": 2,
            "environment": BOT_ENVIRONMENT,
        }

        # Act
        answer = read_check_logs(request, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "logs": [{"name": "jenkins", "tail": None}]})

    def test_should_run_gh_in_the_repository_as_the_login_of_the_environment(self):
        # Arrange
        gh = create_gh_answering_by_argv({CHECKS_OF_PULL_REQUEST_42: json.dumps([])})
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "number": 42,
            "checks": [],
            "lines": 2,
            "environment": BOT_ENVIRONMENT,
        }

        # Act
        read_check_logs(request, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=CHECKS_OF_PULL_REQUEST_42,
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


REVIEW_THREADS_REQUEST = {
    "schema_version": 1,
    "repository": "/projects/shop",
    "number": 42,
    "environment": BOT_ENVIRONMENT,
}


def create_review_threads_page(threads: list[dict]) -> str:
    return json.dumps({"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": threads}}}}})


class ListReviewThreadsTest(unittest.TestCase):
    def test_should_answer_each_open_thread_by_its_identifier_with_its_first_comment(self):
        # Arrange
        gh = create_gh(
            create_review_threads_page(
                [
                    {
                        "id": "PRRT_kwDOA1",
                        "isResolved": False,
                        "path": "src/cart.py",
                        "line": 12,
                        "comments": {"nodes": [{"author": {"login": "octo-reviewer"}, "body": "the total is wrong"}]},
                    }
                ]
            )
        )
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = list_review_threads(REVIEW_THREADS_REQUEST, runtime)

        # Assert
        self.assertEqual(
            answer,
            {
                "schema_version": 1,
                "threads": [
                    {
                        "id": "PRRT_kwDOA1",
                        "file": "src/cart.py",
                        "line": 12,
                        "author": "octo-reviewer",
                        "body": "the total is wrong",
                    }
                ],
            },
        )

    def test_should_leave_out_a_resolved_thread(self):
        # Arrange
        gh = create_gh(
            create_review_threads_page(
                [
                    {
                        "id": "PRRT_kwDOA2",
                        "isResolved": True,
                        "path": "src/cart.py",
                        "line": 3,
                        "comments": {"nodes": [{"author": {"login": "octo-reviewer"}, "body": "rename it"}]},
                    }
                ]
            )
        )
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = list_review_threads(REVIEW_THREADS_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "threads": []})

    def test_should_name_no_author_for_a_comment_of_a_deleted_account(self):
        # Arrange
        gh = create_gh(
            create_review_threads_page(
                [
                    {
                        "id": "PRRT_kwDOA3",
                        "isResolved": False,
                        "path": "src/cart.py",
                        "line": None,
                        "comments": {"nodes": [{"author": None, "body": "outdated"}]},
                    }
                ]
            )
        )
        runtime = create_test_runtime(run_process=gh)

        # Act
        answer = list_review_threads(REVIEW_THREADS_REQUEST, runtime)

        # Assert
        self.assertEqual(answer["threads"][0]["author"], None)

    def test_should_ask_the_threads_of_the_pull_request_in_the_repository_as_the_login_of_the_environment(self):
        # Arrange
        gh = create_gh(create_review_threads_page([]))
        runtime = create_test_runtime(run_process=gh)

        # Act
        list_review_threads(REVIEW_THREADS_REQUEST, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
                        "gh",
                        "api",
                        "graphql",
                        "-F",
                        "owner={owner}",
                        "-F",
                        "name={repo}",
                        "-F",
                        "number=42",
                        "-f",
                        f"query={REVIEW_THREADS_QUERY}",
                    ),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


class ReplyReviewThreadTest(unittest.TestCase):
    def test_should_reply_on_the_thread_with_the_body_as_the_login_of_the_environment(self):
        # Arrange
        gh = create_gh(json.dumps({"data": {}}))
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "thread": "PRRT_kwDOA1",
            "body": "fixed by 8885daa",
            "environment": BOT_ENVIRONMENT,
        }

        # Act
        answer = reply_review_thread(request, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1})
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
                        "gh",
                        "api",
                        "graphql",
                        "-f",
                        "thread=PRRT_kwDOA1",
                        "-f",
                        "body=fixed by 8885daa",
                        "-f",
                        f"query={THREAD_REPLY_MUTATION}",
                    ),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment=BOT_ENVIRONMENT,
                )
            ],
        )


CLI_ENVIRONMENT = {"GH_TOKEN": "token-of-octo-cli"}
NO_LINK = None
CHECK_RUNS_REQUEST = {
    "schema_version": 1,
    "repository": "/projects/shop",
    "branch": "main",
    "environment": CLI_ENVIRONMENT,
}
OPEN_PULL_REQUESTS_PAGES = json.dumps(
    [
        {
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [
                            {
                                "number": 12,
                                "headRefName": "task/shop_w1/S3",
                                "commits": {
                                    "nodes": [
                                        {
                                            "commit": {
                                                "oid": "0123abc",
                                                "statusCheckRollup": {
                                                    "contexts": {
                                                        "nodes": [
                                                            {
                                                                "__typename": "CheckRun",
                                                                "name": "tests",
                                                                "conclusion": "FAILURE",
                                                                "detailsUrl": "https://github.com/octo/shop/actions/runs/7/job/70",
                                                            },
                                                            {
                                                                "__typename": "CheckRun",
                                                                "name": "lint",
                                                                "conclusion": None,
                                                                "detailsUrl": None,
                                                            },
                                                            {"__typename": "StatusContext"},
                                                        ]
                                                    }
                                                },
                                            }
                                        }
                                    ]
                                },
                            },
                            {
                                "number": 13,
                                "headRefName": "docs/readme",
                                "commits": {"nodes": [{"commit": {"oid": "89abcde", "statusCheckRollup": None}}]},
                            },
                        ]
                    }
                }
            }
        }
    ]
)
MAIN_HEAD = json.dumps(
    {
        "data": {
            "repository": {
                "ref": {
                    "target": {
                        "oid": "4567def",
                        "statusCheckRollup": {
                            "contexts": {
                                "nodes": [
                                    {
                                        "__typename": "CheckRun",
                                        "name": "build",
                                        "conclusion": "TIMED_OUT",
                                        "detailsUrl": "https://ci.example.com/build/9",
                                    }
                                ]
                            }
                        },
                    }
                }
            }
        }
    }
)
MISSING_BRANCH = json.dumps({"data": {"repository": {"ref": None}}})
NO_OPEN_PULL_REQUEST = json.dumps([{"data": {"repository": {"pullRequests": {"nodes": []}}}}])
JOB = json.dumps(
    {
        "id": 70,
        "steps": [
            {"name": "Set up job", "status": "completed", "conclusion": "success", "number": 1},
            {"name": "Run tests", "status": "completed", "conclusion": "failure", "number": 2},
            {"name": "Post Run actions/checkout@v4", "status": "pending", "conclusion": None, "number": 3},
        ],
    }
)


class ListCheckRunsTest(unittest.TestCase):
    def test_should_answer_the_check_runs_of_the_open_pull_requests_and_of_the_head_of_the_branch(self):
        # Arrange
        runtime = create_test_runtime(run_process=create_gh_answering_in_turn([OPEN_PULL_REQUESTS_PAGES, MAIN_HEAD]))

        # Act
        answer = list_check_runs(CHECK_RUNS_REQUEST, runtime)

        # Assert
        self.assertEqual(
            answer,
            {
                "schema_version": 1,
                "check_runs": [
                    {
                        "pull_request": 12,
                        "branch": "task/shop_w1/S3",
                        "head": "0123abc",
                        "name": "tests",
                        "conclusion": "failure",
                        "link": "https://github.com/octo/shop/actions/runs/7/job/70",
                    },
                    {
                        "pull_request": 12,
                        "branch": "task/shop_w1/S3",
                        "head": "0123abc",
                        "name": "lint",
                        "conclusion": "pending",
                        "link": None,
                    },
                    {
                        "pull_request": None,
                        "branch": "main",
                        "head": "4567def",
                        "name": "build",
                        "conclusion": "timed_out",
                        "link": "https://ci.example.com/build/9",
                    },
                ],
            },
        )

    def test_should_answer_no_check_run_of_a_branch_the_forge_does_not_hold(self):
        # Arrange
        runtime = create_test_runtime(run_process=create_gh_answering_in_turn([NO_OPEN_PULL_REQUEST, MISSING_BRANCH]))

        # Act
        answer = list_check_runs(CHECK_RUNS_REQUEST, runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1, "check_runs": []})

    def test_should_read_every_page_of_the_open_pull_requests_then_the_branch_as_the_login_of_the_request(self):
        # Arrange
        gh = create_gh_answering_in_turn([NO_OPEN_PULL_REQUEST, MISSING_BRANCH])
        runtime = create_test_runtime(run_process=gh)

        # Act
        list_check_runs(CHECK_RUNS_REQUEST, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=(
                        "gh",
                        "api",
                        "graphql",
                        "--paginate",
                        "--slurp",
                        "-F",
                        "owner={owner}",
                        "-F",
                        "name={repo}",
                        "-f",
                        f"query={OPEN_CHECK_RUNS_QUERY}",
                    ),
                    cwd="/projects/shop",
                    timeout_s=600.0,
                    environment={"GH_TOKEN": "token-of-octo-cli"},
                ),
                ProcessRequest(
                    argv=(
                        "gh",
                        "api",
                        "graphql",
                        "-F",
                        "owner={owner}",
                        "-F",
                        "name={repo}",
                        "-f",
                        "branch=refs/heads/main",
                        "-f",
                        f"query={BRANCH_CHECK_RUNS_QUERY}",
                    ),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment={"GH_TOKEN": "token-of-octo-cli"},
                ),
            ],
        )


class ReadJobStepsTest(unittest.TestCase):
    def test_should_answer_the_steps_of_the_job_the_link_names(self):
        # Arrange
        gh = create_gh_answering_in_turn([JOB])
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "link": "https://github.com/octo/shop/actions/runs/7/job/70",
            "environment": CLI_ENVIRONMENT,
        }

        # Act
        answer = read_job_steps(request, runtime)

        # Assert
        self.assertEqual(
            answer,
            {
                "schema_version": 1,
                "steps": [
                    {"name": "Set up job", "conclusion": "success"},
                    {"name": "Run tests", "conclusion": "failure"},
                    {"name": "Post Run actions/checkout@v4", "conclusion": None},
                ],
            },
        )

    def test_should_ask_gh_for_the_job_the_link_names_as_the_login_of_the_request(self):
        # Arrange
        gh = create_gh_answering_in_turn([JOB])
        runtime = create_test_runtime(run_process=gh)
        request = {
            "schema_version": 1,
            "repository": "/projects/shop",
            "link": "https://github.com/octo/shop/actions/runs/7/job/70",
            "environment": CLI_ENVIRONMENT,
        }

        # Act
        read_job_steps(request, runtime)

        # Assert
        self.assertEqual(
            gh.requests,
            [
                ProcessRequest(
                    argv=("gh", "api", "repos/{owner}/{repo}/actions/jobs/70"),
                    cwd="/projects/shop",
                    timeout_s=60.0,
                    environment={"GH_TOKEN": "token-of-octo-cli"},
                )
            ],
        )

    def test_should_answer_no_steps_for_a_link_naming_no_job(self):
        for link in [
            "https://ci.example.com/build/9",
            "https://jenkins.example.com/job/oak/job/main/12/display/redirect",
            NO_LINK,
        ]:
            with self.subTest(link=link):
                # Arrange
                runtime = create_test_runtime(run_process=create_gh_answering_in_turn([]))
                request = {"schema_version": 1, "repository": "/projects/shop", "link": link, "environment": {}}

                # Act
                answer = read_job_steps(request, runtime)

                # Assert
                self.assertEqual(answer, {"schema_version": 1, "steps": None})
