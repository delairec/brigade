from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_verdict import TaskVerdict
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details
from brigade.system.parse_configuration import Configuration
from brigade.system.read_account_environment import ForgeAccount, read_account_environment
from brigade.verify.read_review_mode import APPROVAL_REVIEW, read_review_mode
from brigade.verify.validate_verdict import PASSING_VERDICT

DOCUMENT_SCHEMA_VERSION = 1
FORGE_NAME = "github"
CLI_KEY = "cli"
REVIEW_SLOT = "review"
APPROVING_REVIEW = "approve"
REQUESTING_REVIEW = "request_changes"


@dataclass(frozen=True)
class VerdictDemand:
    project_path: str
    opened: TaskPrOpened
    verdict: dict
    forge: object
    configuration: Configuration


def _read_environment(runtime: Runtime, demand: VerdictDemand, key: str) -> dict:
    account = ForgeAccount(forge=demand.forge, forge_name=FORGE_NAME, key=key)
    return read_account_environment(account, demand.configuration, runtime)


def _render_review_body(verdict: dict) -> str:
    findings = "".join(
        f"- {finding['grade']} {finding['file']}:{finding['line']}: {finding['broken']}\n"
        for finding in verdict["findings"]
    )
    return f"verdict {verdict['verdict']}\n{findings}"


def _post_review(runtime: Runtime, demand: VerdictDemand, head: str) -> str | None:
    environment = _read_environment(runtime, demand, REVIEW_SLOT)
    demand.forge.post_review(
        {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "repository": demand.project_path,
            "number": demand.opened.pr,
            "event": APPROVING_REVIEW if demand.verdict["verdict"] == PASSING_VERDICT else REQUESTING_REVIEW,
            "commit": head,
            "body": _render_review_body(demand.verdict),
            "environment": environment,
        },
        runtime,
    )
    return ask_forge_account(demand.forge, FORGE_NAME, environment, runtime).login


def record_verdict(runtime: Runtime, demand: VerdictDemand) -> dict:
    opened = demand.opened
    pull_request = ask_pull_request_details(
        demand.forge,
        FORGE_NAME,
        PullRequestDetailsQuery(
            repository=demand.project_path,
            number=opened.pr,
            environment=_read_environment(runtime, demand, CLI_KEY),
        ),
        runtime,
    )
    judged, head = demand.verdict["head"], pull_request["head_sha"]
    if judged != head:
        raise BrigadeError(f"the verdict judged {judged}, no longer the head of #{opened.pr}, now {head}")
    approving = read_review_mode(runtime, opened.project) == APPROVAL_REVIEW
    event = TaskVerdict(
        project=opened.project,
        wave=opened.wave,
        task=opened.task,
        pr=opened.pr,
        head=head,
        verdict=demand.verdict["verdict"],
        findings=tuple(demand.verdict["findings"]),
        login=_post_review(runtime, demand, head) if approving else None,
    )
    append_event(runtime.paths, runtime.now, event)
    return event.to_document()
