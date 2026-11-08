import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.rebase_pr import COMMAND
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.repair_pr_opened import RepairPrOpened
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

WORKTREE = "/srv/oak-repair"
FIX_BRANCH = "fix/repair-main-c0ffee"
BOUND_ACCOUNTS = (
    'attribution = ["Co-Authored-By: Ada <ada@example.org>"]\n'
    '[forge_accounts]\nbuild = "octo-bot"\nrebase = "fix-bot"\n'
)
OPENED_PULL_REQUEST = {"number": 91, "url": "https://github.com/acme/oak/pull/91"}
OPENED_DOCUMENT = {
    "schema_version": 1,
    "project": "oak",
    "branch": FIX_BRANCH,
    "into": "main",
    "title": "fix(parser): restore the parsing of an empty line",
    "pr": 91,
    "url": "https://github.com/acme/oak/pull/91",
    "login": "fix-bot",
}


def _answer_the_token_of_the_login(request: dict) -> dict:
    return {"schema_version": 1, "environment": {"GH_TOKEN": f"token-of-{request['login']}"}}


def _answer_the_login_of_the_token(request: dict) -> dict:
    return {"schema_version": 1, "login": request["environment"]["GH_TOKEN"].removeprefix("token-of-")}


class RebasePrTextTest(unittest.TestCase):
    def test_should_print_the_address_of_the_pull_request(self):
        # Act
        text = COMMAND.render_text(OPENED_DOCUMENT)

        # Assert
        self.assertEqual(text, "https://github.com/acme/oak/pull/91")


class RebasePrRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(into="main")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RebasePrExitCodeTest(unittest.TestCase):
    def test_should_exit_0(self):
        # Act
        exit_code = COMMAND.decide_exit_code(OPENED_DOCUMENT)

        # Assert
        self.assertEqual(exit_code, 0)


class RebasePrOfARepairBranchTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "config.toml").write_text(BOUND_ACCOUNTS, encoding="utf-8")
        self.processes = ScriptedProcesses()
        self.forge = ForgeDouble(
            {
                "read_login_environment": _answer_the_token_of_the_login,
                "describe_account": _answer_the_login_of_the_token,
                "open_pull_request": lambda request: OPENED_PULL_REQUEST,
            }
        )
        self.runtime = create_test_runtime(
            create_test_paths(root), run_process=self.processes, resolve_plugin=lambda kind, name, **places: self.forge
        )
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout=f"{WORKTREE}\n")
        self.processes.answer(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n"
        )
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"), ("FORGE", "github"))}
        )
        self.processes.answer(("git", "branch", "--show-current"), stdout=f"{FIX_BRANCH}\n")
        self.processes.answer(
            ("git", "log", "-1", "--format=%s", "HEAD"), stdout="fix(parser): restore the parsing of an empty line\n"
        )
        self.pushed_environments = []
        self.processes.answer_by(("git", "push", "--quiet", "origin", FIX_BRANCH), self.record_push)

    def record_push(self, request):
        self.pushed_environments.append(request.environment)
        return 0, "", ""

    def test_should_push_the_repair_branch_as_the_login_of_the_rebase_slot(self):
        # Act
        COMMAND.run(Namespace(into="main"), self.runtime)

        # Assert
        self.assertEqual(self.pushed_environments, [{"GH_TOKEN": "token-of-fix-bot"}])

    def test_should_open_the_pull_request_into_the_main_branch_through_the_forge_adapter(self):
        # Act
        COMMAND.run(Namespace(into="main"), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.list_requests("open_pull_request"),
            [
                {
                    "repository": WORKTREE,
                    "base": "main",
                    "branch": FIX_BRANCH,
                    "title": "fix(parser): restore the parsing of an empty line",
                    "body": f"Repairs the red head of main on {FIX_BRANCH}.\n\nCo-Authored-By: Ada <ada@example.org>\n",
                    "milestone": None,
                    "environment": {"GH_TOKEN": "token-of-fix-bot"},
                }
            ],
        )

    def test_should_record_in_the_ledger_the_login_the_pull_request_was_opened_as(self):
        # Act
        COMMAND.run(Namespace(into="main"), self.runtime)

        # Assert
        self.assertEqual(
            read_ledger(self.runtime.paths.state_root).entries[-1].event,
            RepairPrOpened(project="oak", branch=FIX_BRANCH, into="main", pr=91, login="fix-bot"),
        )

    def test_should_describe_the_pull_request_opened(self):
        # Act
        document = COMMAND.run(Namespace(into="main"), self.runtime)

        # Assert
        self.assertEqual(document, OPENED_DOCUMENT)


if __name__ == "__main__":
    unittest.main()
