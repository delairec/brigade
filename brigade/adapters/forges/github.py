import json

from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest

HOST = "github.com"
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
DOCUMENT_SCHEMA_VERSION = 1
AUTHENTICATION_VARIABLE = "GH_TOKEN"
PUBLICATION_TIMEOUT_S = 60.0
BODY_FROM_STDIN = "-"
URL_SEPARATOR = "/"
UNBOUND_ENVIRONMENT = {}
MILESTONES_PATH = "repos/{owner}/{repo}/milestones"
MILESTONES_OF_EVERY_STATE = f"{MILESTONES_PATH}?state=all"
PULL_REQUEST_FIELDS = "number,state,headRefOid,baseRefName,reviewDecision,statusCheckRollup"
PULL_REQUEST_DETAIL_FIELDS = "number,title,body,headRefName,headRefOid,statusCheckRollup"
PULL_REQUESTS_QUERY = """query($owner: String!, $name: String!, $states: [PullRequestState!], $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, after: $endCursor, states: $states, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number title headRefName baseRefName state isDraft reviewDecision
        author { login }
        commits(last: 1) {
          nodes { commit { statusCheckRollup { contexts(first: 100) {
            nodes { __typename ... on CheckRun { name conclusion } }
          } } } }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""
EVERY_STATE = "all"
LISTING_TIMEOUT_S = 600.0
COMPARE_PATH = "repos/{owner}/{repo}/compare"
CHECK_RUN_TYPE = "CheckRun"
PENDING_VERDICT = "pending"
REVIEW_EVENTS = {"approve": "APPROVE", "request_changes": "REQUEST_CHANGES"}


def _read_active_login(hosts_document: str):
    try:
        accounts = json.loads(hosts_document)["hosts"][HOST]
    except (ValueError, KeyError, TypeError):
        return None
    return next((account.get("login") for account in accounts if account.get("active")), None)


def read_login_environment(request: dict, runtime: Runtime) -> dict:
    record = runtime.run_process(
        ProcessRequest(
            argv=("gh", "auth", "token", "--hostname", HOST, "--user", request["login"]),
            cwd=PROBE_DIRECTORY,
            timeout_s=PROBE_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    token = record.stdout.strip() if record.exit_code == 0 else ""
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "environment": {AUTHENTICATION_VARIABLE: token} if token else None,
    }


def describe_account(request: dict, runtime: Runtime) -> dict:
    record = runtime.run_process(
        ProcessRequest(
            argv=("gh", "auth", "status", "--active", "--hostname", HOST, "--json", "hosts"),
            cwd=PROBE_DIRECTORY,
            timeout_s=PROBE_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
            environment=request["environment"],
        )
    )
    login = _read_active_login(record.stdout) if record.exit_code == 0 else None
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "login": login}


def _publish(request: dict, runtime: Runtime, argv: tuple[str, ...], environment: dict) -> str:
    record = runtime.run_process(
        ProcessRequest(
            argv=(*argv, "--title", request["title"], "--body-file", BODY_FROM_STDIN),
            cwd=request["repository"],
            timeout_s=PUBLICATION_TIMEOUT_S,
            stdin=request["body"],
            environment=environment,
        )
    )
    return record.stdout.strip()


def _describe_milestone(milestone: str | None) -> tuple[str, ...]:
    if milestone is None:
        return ()
    return ("--milestone", milestone)


def open_pull_request(request: dict, runtime: Runtime) -> dict:
    url = _publish(
        request,
        runtime,
        (
            "gh",
            "pr",
            "create",
            "--base",
            request["base"],
            "--head",
            request["branch"],
            *_describe_milestone(request["milestone"]),
        ),
        request["environment"],
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "url": url, "number": int(url.rsplit(URL_SEPARATOR, 1)[1])}


def open_issue(request: dict, runtime: Runtime) -> dict:
    url = _publish(request, runtime, ("gh", "issue", "create"), UNBOUND_ENVIRONMENT)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "url": url}


def _ask_milestones_api(request: dict, runtime: Runtime, arguments: tuple[str, ...]) -> str:
    record = runtime.run_process(
        ProcessRequest(
            argv=("gh", "api", *arguments),
            cwd=request["repository"],
            timeout_s=PUBLICATION_TIMEOUT_S,
            environment=request["environment"],
        )
    )
    return record.stdout


def list_milestones(request: dict, runtime: Runtime) -> dict:
    titles = _ask_milestones_api(request, runtime, ("--paginate", MILESTONES_OF_EVERY_STATE, "--jq", ".[].title"))
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "titles": titles.splitlines()}


def create_milestone(request: dict, runtime: Runtime) -> dict:
    _ask_milestones_api(request, runtime, ("--method", "POST", MILESTONES_PATH, "-f", f"title={request['title']}"))
    return {"schema_version": DOCUMENT_SCHEMA_VERSION}


def _ask_gh(request: dict, runtime: Runtime, arguments: tuple[str, ...]) -> str:
    record = runtime.run_process(
        ProcessRequest(
            argv=("gh", *arguments),
            cwd=request["repository"],
            timeout_s=PUBLICATION_TIMEOUT_S,
            environment=request["environment"],
        )
    )
    return record.stdout


def _describe_check_run(check_run: dict) -> dict:
    return {"name": check_run["name"], "verdict": (check_run["conclusion"] or PENDING_VERDICT).lower()}


def _describe_check_runs(status_check_rollup: list) -> list[dict]:
    return [_describe_check_run(check) for check in status_check_rollup if check["__typename"] == CHECK_RUN_TYPE]


def _describe_review(review_decision: str | None) -> str | None:
    if not review_decision:
        return None
    return review_decision.lower()


def _read_login(author: dict | None) -> str | None:
    if author is None:
        return None
    return author["login"]


def _read_check_contexts(pull_request: dict) -> list:
    rollup = pull_request["commits"]["nodes"][0]["commit"]["statusCheckRollup"]
    if rollup is None:
        return []
    return rollup["contexts"]["nodes"]


def _describe_listed_pull_request(pull_request: dict) -> dict:
    return {
        "number": pull_request["number"],
        "title": pull_request["title"],
        "head": pull_request["headRefName"],
        "base": pull_request["baseRefName"],
        "state": pull_request["state"].lower(),
        "author": _read_login(pull_request["author"]),
        "draft": pull_request["isDraft"],
        "review": _describe_review(pull_request["reviewDecision"]),
        "checks": _describe_check_runs(_read_check_contexts(pull_request)),
    }


def _describe_states(state: str) -> tuple[str, ...]:
    if state == EVERY_STATE:
        return ()
    return ("-f", f"states[]={state.upper()}")


def list_pull_requests(request: dict, runtime: Runtime) -> dict:
    record = runtime.run_process(
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
                *_describe_states(request["state"]),
                "-f",
                f"query={PULL_REQUESTS_QUERY}",
            ),
            cwd=request["repository"],
            timeout_s=LISTING_TIMEOUT_S,
            environment=request["environment"],
        )
    )
    pages = json.loads(record.stdout)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "pull_requests": [
            _describe_listed_pull_request(pull_request)
            for page in pages
            for pull_request in page["data"]["repository"]["pullRequests"]["nodes"]
        ],
    }


def find_pull_request(request: dict, runtime: Runtime) -> dict:
    found = json.loads(
        _ask_gh(
            request,
            runtime,
            (
                "pr",
                "list",
                "--head",
                request["branch"],
                "--state",
                "all",
                "--limit",
                "1",
                "--json",
                PULL_REQUEST_FIELDS,
            ),
        )
    )
    if not found:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, "pull_request": None}
    pull_request = found[0]
    behind_by = _ask_gh(
        request,
        runtime,
        ("api", f"{COMPARE_PATH}/{pull_request['baseRefName']}...{pull_request['headRefOid']}", "--jq", ".behind_by"),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "pull_request": {
            "number": pull_request["number"],
            "state": pull_request["state"].lower(),
            "checks": _describe_check_runs(pull_request["statusCheckRollup"]),
            "review": _describe_review(pull_request["reviewDecision"]),
            "behind": int(behind_by) > 0,
            "head": pull_request["headRefOid"],
        },
    }


def read_pull_request(request: dict, runtime: Runtime) -> dict:
    pull_request = json.loads(
        _ask_gh(request, runtime, ("pr", "view", str(request["number"]), "--json", PULL_REQUEST_DETAIL_FIELDS))
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "pull_request": {
            "number": pull_request["number"],
            "title": pull_request["title"],
            "body": pull_request["body"],
            "head": pull_request["headRefName"],
            "head_sha": pull_request["headRefOid"],
            "checks": _describe_check_runs(pull_request["statusCheckRollup"]),
        },
    }


def post_review(request: dict, runtime: Runtime) -> dict:
    runtime.run_process(
        ProcessRequest(
            argv=(
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/pulls/{request['number']}/reviews",
                "--method",
                "POST",
                "-f",
                f"event={REVIEW_EVENTS[request['event']]}",
                "-f",
                f"commit_id={request['commit']}",
                "-F",
                "body=@-",
            ),
            cwd=request["repository"],
            timeout_s=PUBLICATION_TIMEOUT_S,
            stdin=request["body"],
            environment=request["environment"],
        )
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION}
