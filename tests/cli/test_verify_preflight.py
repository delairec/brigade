import json
import os
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_collect import install_executable
from tests.cli.test_task import TASK_BRANCH, WAVE_BRANCH, TaskContextTestCase
from tests.cli.test_task_pr import TYPED_SCHEMA

DELIVERED_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY 42\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\t\tIMPL "src/cart/button.py::def empty_cart"\n'
    '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def charge"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
WAVE_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
BUTTON_SOURCE = "def empty_cart(cart):\n    cart.clear()\n"
CHARGE_SOURCE = "def charge(cart):\n    return 0\n"
PEER_SOURCE = "def weigh(parcel):\n    return 1\n"
PULL_REQUEST_TITLE = "feat(cart-button): empty the cart in one click (@TASK.S3)"
PULL_REQUEST_BODY = (
    "Empty the cart in one click\n\n## Acceptance criteria\n\n"
    "- the button of src/cart/button.py, once pressed, empties the cart\n- the emptying charges nothing\n\n"
    "## Checks of 0123abc\n\n- pass `python3 -m unittest` 1.0 s\n"
)
SUCCESSFUL_CHECK_RUN = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}
FAKE_GH = (
    "#!/bin/sh\n"
    'printf \'%s\\n\' "$*" >> "{calls}"\n'
    'case "$1 $2" in\n'
    '  "auth token") echo token-of-octo-cli ;;\n'
    '  "pr view") cat "{pull_request}" ;;\n'
    "esac\n"
)
CLI_KEYS = '[forge_accounts]\ncli = "octo-cli"\n'
LEDGER_LINES = (
    '{"schema_version": 2, "ts": "2026-10-17T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-17T12:00:00Z", "event": "task.pr_opened", "project": "shop",'
    f' "task": "S3", "wave": "shop_w1", "branch": "{TASK_BRANCH}", "pr": 42, "login": "octo-bot"}}\n'
)


class VerifyPreflightTestCase(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name).resolve()
        self.gh_calls = root / "gh-calls"
        self.pull_request = root / "pull-request.json"
        install_executable(root / "tools" / "gh", FAKE_GH.format(calls=self.gh_calls, pull_request=self.pull_request))
        self.configure(keys=CLI_KEYS)
        self.commit_in_worktree({"corpus/_schema.awawa": TYPED_SCHEMA, "corpus/tasks.awawa": WAVE_TASKS}, "the plan")
        self.project.run_git("branch", "--force", WAVE_BRANCH, TASK_BRANCH)
        self.commit_in_worktree(
            {
                "corpus/tasks.awawa": DELIVERED_TASKS,
                "src/cart/button.py": BUTTON_SOURCE,
                "src/billing/charge.py": CHARGE_SOURCE,
            },
            "the delivery",
        )
        self.remote = root / "remotes" / "shop.git"
        self.project.run_git("init", "--quiet", "--bare", str(self.remote))
        self.project.run_git("remote", "add", "origin", str(self.remote))
        self.project.run_git("push", "--quiet", "origin", WAVE_BRANCH, TASK_BRANCH)
        ledger = self.state / "ledger" / "2026-10.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(LEDGER_LINES)
        self.describe_pull_request()

    def describe_environment(self) -> dict:
        tools = Path(self.root.name).resolve() / "tools"
        return {**super().describe_environment(), "PATH": f"{tools}{os.pathsep}{self.machine.search_path}"}

    def commit_in_worktree(self, files: dict, message: str) -> None:
        for relative_path, content in files.items():
            path = self.worktree / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.project.run_git("-C", str(self.worktree), "add", "--all")
        self.project.run_git("-C", str(self.worktree), "commit", "--quiet", "-m", message)

    def read_head(self) -> str:
        return self.project.run_git("-C", str(self.worktree), "rev-parse", "HEAD").strip()

    def describe_pull_request(
        self,
        title: str = PULL_REQUEST_TITLE,
        body: str = PULL_REQUEST_BODY,
        check_runs: tuple = (SUCCESSFUL_CHECK_RUN,),
    ) -> None:
        self.pull_request.write_text(
            json.dumps(
                {
                    "number": 42,
                    "title": title,
                    "body": body,
                    "headRefName": TASK_BRANCH,
                    "headRefOid": self.read_head(),
                    "statusCheckRollup": list(check_runs),
                }
            )
        )

    def run_preflight(self, *arguments: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "verify",
            "preflight",
            *arguments,
            environment=self.describe_environment(),
            cwd=self.project.path,
        )

    def read_checks(self) -> dict:
        completed = self.run_preflight("42", "--json")
        return {check["name"]: check for check in json.loads(completed.stdout)["checks"]}


class BrigadeVerifyPreflightOfASoundPullRequestTest(VerifyPreflightTestCase):
    def test_should_print_one_passing_entry_per_check_and_the_size_as_information(self):
        # Act
        completed = self.run_preflight("42", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "project": "shop",
                "pr": 42,
                "task": "S3",
                "head": self.read_head(),
                "checks": [
                    {"name": "ancestry", "verdict": "pass", "findings": []},
                    {"name": "checks", "verdict": "pass", "findings": []},
                    {"name": "corpus", "verdict": "pass", "findings": []},
                    {"name": "promotion", "verdict": "pass", "findings": []},
                    {"name": "untouched_files", "verdict": "pass", "findings": []},
                    {"name": "privacy", "verdict": "pass", "findings": []},
                    {"name": "body", "verdict": "pass", "findings": []},
                    {
                        "name": "size",
                        "verdict": "info",
                        "findings": ["3 files", "9 lines", "3 packages: corpus, src/billing, src/cart", "0 layers"],
                    },
                ],
            },
        )

    def test_should_exit_0_when_no_check_fails(self):
        # Act
        completed = self.run_preflight("42")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_should_print_one_line_per_check_its_verdict_and_its_name(self):
        # Act
        completed = self.run_preflight("42")

        # Assert
        self.assertEqual(
            completed.stdout,
            f"preflight of #42, @TASK.S3 at {self.read_head()}\n"
            "pass  ancestry\npass  checks\npass  corpus\npass  promotion\npass  untouched_files\npass  privacy\n"
            "pass  body\ninfo  size\n  3 files\n  9 lines\n  3 packages: corpus, src/billing, src/cart\n  0 layers\n",
        )

    def test_should_read_the_pull_request_as_the_login_of_the_key_cli(self):
        # Act
        self.run_preflight("42")

        # Assert
        self.assertIn("auth token --hostname github.com --user octo-cli\n", self.gh_calls.read_text())


class BrigadeVerifyPreflightOfAPullRequestBehindItsWaveTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        peer = Path(self.root.name).resolve() / "peer"
        self.project.run_git("clone", "--quiet", "--branch", WAVE_BRANCH, str(self.remote), str(peer))
        (peer / "src" / "shipping").mkdir(parents=True)
        (peer / "src" / "shipping" / "parcel.py").write_text(PEER_SOURCE)
        self.project.run_git("-C", str(peer), "add", "--all")
        self.project.run_git("-C", str(peer), "commit", "--quiet", "-m", "a peer merged")
        self.project.run_git("-C", str(peer), "push", "--quiet", "origin", WAVE_BRANCH)
        self.wave_head = self.project.run_git("-C", str(peer), "rev-parse", "HEAD").strip()

    def test_should_fail_the_ancestry_naming_the_head_of_the_branch_of_the_wave(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["ancestry"],
            {
                "name": "ancestry",
                "verdict": "fail",
                "findings": [f"{self.read_head()} does not descend from {WAVE_BRANCH} at {self.wave_head}"],
            },
        )

    def test_should_measure_the_size_from_the_fork_of_the_branch_of_the_wave(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["size"],
            {
                "name": "size",
                "verdict": "info",
                "findings": ["3 files", "9 lines", "3 packages: corpus, src/billing, src/cart", "0 layers"],
            },
        )

    def test_should_exit_1_when_a_check_fails(self):
        # Act
        completed = self.run_preflight("42")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)


class BrigadeVerifyPreflightOfAPullRequestWithUnfinishedChecksTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        self.describe_pull_request(
            check_runs=(
                SUCCESSFUL_CHECK_RUN,
                {"__typename": "CheckRun", "name": "lint", "status": "IN_PROGRESS", "conclusion": None},
                {"__typename": "CheckRun", "name": "e2e", "status": "COMPLETED", "conclusion": "FAILURE"},
                {"__typename": "StatusContext", "context": "deploy", "state": "PENDING"},
            )
        )

    def test_should_fail_the_checks_naming_each_check_run_not_completed_and_successful(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["checks"], {"name": "checks", "verdict": "fail", "findings": ["lint: pending", "e2e: failure"]}
        )


class BrigadeVerifyPreflightOfANonCanonicalCorpusTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        self.commit_in_worktree(
            {"corpus/milestones.awawa": 'MILESTONE M1\n\tTITLE   "Empty cart"\n\tSTATUS running\n'}, "a reflow"
        )
        self.project.run_git("push", "--quiet", "origin", TASK_BRANCH)
        self.describe_pull_request()

    def test_should_fail_the_corpus_on_the_check_of_the_format(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["corpus"],
            {
                "name": "corpus",
                "verdict": "fail",
                "findings": ["awawa fmt --check . exited 1", "would reformat ./corpus/milestones.awawa"],
            },
        )

    def test_should_fail_the_untouched_files_on_a_file_whose_entities_did_not_change(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["untouched_files"],
            {
                "name": "untouched_files",
                "verdict": "fail",
                "findings": ["corpus/milestones.awawa changes while none of its entities does"],
            },
        )


class BrigadeVerifyPreflightOfAPullRequestRemovingTheEntitiesOfAFileTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        self.project.run_git("-C", str(self.worktree), "rm", "--quiet", "corpus/milestones.awawa")
        self.project.run_git("-C", str(self.worktree), "commit", "--quiet", "-m", "the milestones removed")
        self.project.run_git("push", "--quiet", "origin", TASK_BRANCH)
        self.describe_pull_request()

    def test_should_pass_the_untouched_files_on_a_file_whose_entities_are_removed(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(checks["untouched_files"], {"name": "untouched_files", "verdict": "pass", "findings": []})


class BrigadeVerifyPreflightOfACorpusFailingItsLintTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        self.commit_in_worktree(
            {
                "corpus/tasks.awawa": (
                    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
                    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY 42\n'
                    '\tTYPE feat\n\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
                    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
                    '\t\tIMPL "src/cart/button.py::def empty_cart"\n'
                    '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def charge"\n\n'
                    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tOWNER "nobody"\n'
                    "\tMILESTONE @MILESTONE.M1\n"
                )
            },
            "a field no schema declares",
        )
        self.project.run_git("push", "--quiet", "origin", TASK_BRANCH)
        self.describe_pull_request()

    def test_should_fail_the_corpus_on_the_strict_lint(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["corpus"],
            {
                "name": "corpus",
                "verdict": "fail",
                "findings": [
                    "awawa lint --strict . exited 1",
                    "./corpus/tasks.awawa \u2014 1 error(s), 0 warning(s)",
                    "L003  error  ./corpus/tasks.awawa:20:2",
                    "      field OWNER is not declared on TASK",
                    "",
                ],
            },
        )


class BrigadeVerifyPreflightOfAPullRequestWithoutItsPromotionTest(VerifyPreflightTestCase):
    def deliver(self, tasks: str) -> None:
        self.commit_in_worktree({"corpus/tasks.awawa": tasks}, "another promotion")
        self.project.run_git("push", "--quiet", "origin", TASK_BRANCH)
        self.describe_pull_request()

    def test_should_fail_a_task_that_is_not_implemented(self):
        # Arrange
        self.deliver(
            'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tDELIVERED_BY 42\n\tTYPE feat\n'
            '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
            '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
            '\t\tIMPL "src/cart/button.py::def empty_cart"\n'
            '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def charge"\n'
        )

        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(checks["promotion"]["findings"], ["@TASK.S3 is STATUS todo, not implemented"])

    def test_should_fail_a_task_that_names_no_pull_request_delivering_it(self):
        # Arrange
        self.deliver(
            'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tTYPE feat\n'
            '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
            '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
            '\t\tIMPL "src/cart/button.py::def empty_cart"\n'
            '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def charge"\n'
        )

        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(checks["promotion"]["findings"], ["@TASK.S3 is delivered by no pull request, not by #42"])

    def test_should_fail_each_spec_without_an_impl_whose_anchor_resolves_at_the_head(self):
        # Arrange
        self.deliver(
            'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY 42\n\tTYPE feat\n'
            '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
            '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
            '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def refund"\n'
        )

        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["promotion"],
            {
                "name": "promotion",
                "verdict": "fail",
                "findings": [
                    (
                        "SPEC 1 has no IMPL whose anchor resolves: the button of src/cart/button.py, once pressed,"
                        " empties the cart"
                    ),
                    "SPEC 2 has no IMPL whose anchor resolves: the emptying charges nothing",
                ],
            },
        )


class BrigadeVerifyPreflightOfAPullRequestAddingPrivateLinesTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        (self.machine.corpus / "projects.awawa").write_text(
            f'PROJECT shop\n\tPATH "{self.project.path}"\n\tMAIN "main"\n\tCORPUS "corpus"\n'
            '\tACCEPTANCE "python3 -m unittest"\n\tHEAVY "python3 -m unittest discover tests/e2e"\n\tFORGE "none"\n'
            '\tSTATUS active\n\tPRIVATE "stn_[0-9a-f]{12}"\n'
        )
        self.commit_in_worktree(
            {
                "src/cart/notes.py": (
                    "OWNER = 'alice@example.org'\nCLONE = '/home/alice/shop'\nSTATION = 'stn_0123456789ab'\nLIMIT = 3\n"
                )
            },
            "the notes",
        )
        self.project.run_git("push", "--quiet", "origin", TASK_BRANCH)
        self.describe_pull_request()

    def test_should_fail_the_privacy_naming_the_file_and_the_line_of_each_match(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["privacy"]["findings"],
            [
                "src/cart/notes.py:1: an e-mail address",
                "src/cart/notes.py:2: a home path",
                "src/cart/notes.py:3: the PRIVATE pattern stn_[0-9a-f]{12}",
            ],
        )


class BrigadeVerifyPreflightOfAPullRequestAddingPublicExamplesTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        (self.machine.corpus / "projects.awawa").write_text(
            f'PROJECT shop\n\tPATH "{self.project.path}"\n\tMAIN "main"\n\tCORPUS "corpus"\n'
            '\tACCEPTANCE "python3 -m unittest"\n\tHEAVY "python3 -m unittest discover tests/e2e"\n\tFORGE "none"\n'
            '\tSTATUS active\n\tPUBLIC "alice@example\\\\.org"\n\tPUBLIC "/home/alice"\n'
        )
        self.commit_in_worktree(
            {
                "src/cart/notes.py": (
                    "OWNER = 'alice@example.org'\nCLONE = '/home/alice/shop'\n"
                    "REVIEWERS = 'alice@example.org, bob@example.org'\nARCHIVE = '/home/alice.old/shop'\n"
                )
            },
            "the notes",
        )
        self.project.run_git("push", "--quiet", "origin", TASK_BRANCH)
        self.describe_pull_request()

    def test_should_fail_the_privacy_only_on_what_no_public_pattern_matches_whole(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(
            checks["privacy"]["findings"],
            ["src/cart/notes.py:3: an e-mail address", "src/cart/notes.py:4: a home path"],
        )


class BrigadeVerifyPreflightOfAPullRequestWithAWrongBodyTest(VerifyPreflightTestCase):
    def test_should_fail_a_body_that_keeps_a_placeholder_of_the_template(self):
        for body in ["Empty the cart\n\n$checks\n", "Empty the cart\n\n${checks}\n"]:
            with self.subTest(body=body):
                # Arrange
                self.describe_pull_request(body=body)

                # Act
                checks = self.read_checks()

                # Assert
                self.assertEqual(checks["body"]["findings"], ["the body keeps the placeholder $checks"])


class BrigadeVerifyPreflightOfALayeredPullRequestTest(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        self.commit_in_worktree(
            {
                "src/core-cart/domain/cart.py": "CART = []\n",
                "src/core-cart/application/empty_cart.py": "EMPTIED = True\n",
            },
            "the layers",
        )
        self.project.run_git("push", "--quiet", "origin", TASK_BRANCH)
        self.describe_pull_request()

    def test_should_report_the_layers_the_diff_touches(self):
        # Act
        checks = self.read_checks()

        # Assert
        self.assertEqual(checks["size"]["findings"][3], "2 layers: application, domain")


class BrigadeVerifyPreflightOfAPullRequestOfNoTaskTest(VerifyPreflightTestCase):
    def test_should_exit_1_naming_the_pull_request_no_task_opened(self):
        # Act
        completed = self.run_preflight("43")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade verify preflight: no task.pr_opened of @PROJECT.shop names the pull request #43\n"),
        )
