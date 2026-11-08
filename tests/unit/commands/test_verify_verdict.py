import argparse
import json
import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.verify_verdict import COMMAND
from brigade.errors import BrigadeError
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_verdict import TaskVerdict
from brigade.ledger.wave_started import WaveStarted
from tests.unit.commands.command_runtime import create_machine_double, write_ledger
from tests.unit.commands.test_verify_preflight import TASK_PR_OPENED, TASK_WORKTREE, TIDEPOOL_PROJECT, WAVE_STARTED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.verify.test_record_verdict import create_review_forge

PASS = {"head": "8885daa", "verdict": "pass", "findings": []}
CHANGES_WITHOUT_A_FINDING = {"head": "8885daa", "verdict": "changes", "findings": []}
GITHUB_PROJECT = (*TIDEPOOL_PROJECT, ("FORGE", "github"))


def create_document(login: str | None) -> dict:
    return {"pr": 42, "task": "T7", "head": "8885daa", "verdict": "changes", "findings": [], "login": login}


class VerifyVerdictTextTest(unittest.TestCase):
    def test_should_name_the_verdict_the_pull_request_its_head_and_the_login_of_a_posted_review(self):
        # Arrange
        rows = [
            ("no review posted", None, "verdict changes of #42, @TASK.T7 at 8885daa"),
            (
                "a review posted",
                "tidepool-review",
                "verdict changes of #42, @TASK.T7 at 8885daa, posted as tidepool-review",
            ),
        ]
        for case, login, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(create_document(login))

                # Assert
                self.assertEqual(text, expected_text)

    def test_should_name_the_verdict_the_task_and_its_head_of_a_task_without_a_pull_request(self):
        # Arrange
        document = {"task": "T7", "head": "8885daa", "verdict": "pass", "findings": [], "login": None}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "verdict pass of @TASK.T7 at 8885daa")


class VerifyVerdictExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_verdict_is_recorded(self):
        # Act
        exit_code = COMMAND.decide_exit_code(create_document(None))

        # Assert
        self.assertEqual(exit_code, 0)


class VerifyVerdictRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(pr=42, file="verdict.json")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)

    def test_should_take_a_verdict_naming_no_pull_request(self):
        # Arrange
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, (COMMAND,), argparse.ArgumentParser(add_help=False))

        # Act
        options = parser.parse_args(["verify", "verdict", "--file", "verdict.json"])

        # Assert
        self.assertIsNone(options.pr)


class VerifyVerdictOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED])
        self.verdict = self.root / "verdict.json"
        self.forge = create_review_forge()
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double({"PROJECT": {"tidepool": GITHUB_PROJECT}, "POLICY": {}}, TASK_WORKTREE),
            resolve_plugin=lambda kind, name, **places: self.forge,
        )

    def test_should_refuse_a_verdict_file_it_cannot_read(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pr=42, file=str(self.verdict)), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), f"cannot read {self.verdict}: No such file or directory")

    def test_should_refuse_a_verdict_file_naming_what_is_wrong(self):
        # Arrange
        rows = [
            ("a file holding no JSON", "verdict: pass\n", f"the verdict file {self.verdict} holds no JSON document"),
            (
                "changes without a finding",
                json.dumps({"head": "8885daa", "verdict": "changes", "findings": []}),
                f"the verdict file {self.verdict}: a verdict changes names no finding",
            ),
        ]
        for case, content, expected_message in rows:
            with self.subTest(case=case):
                self.verdict.write_text(content, encoding="utf-8")

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    COMMAND.run(Namespace(pr=42, file=str(self.verdict)), self.runtime)

                # Assert
                self.assertEqual(str(raised.exception), expected_message)

    def test_should_record_nothing_on_a_verdict_changes_naming_no_finding(self):
        # Arrange
        self.verdict.write_text(json.dumps(CHANGES_WITHOUT_A_FINDING), encoding="utf-8")

        # Act
        with self.assertRaises(BrigadeError):
            COMMAND.run(Namespace(pr=42, file=str(self.verdict)), self.runtime)

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state"),
            LedgerReading(
                entries=(
                    LedgerEntry(
                        instant=datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
                        event=WaveStarted(wave="tidepool_w16", project="tidepool", tasks=("T7",)),
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 22, 0, tzinfo=UTC),
                        event=TaskPrOpened(
                            project="tidepool",
                            task="T7",
                            wave="tidepool_w16",
                            branch="task/M4-tides/T7",
                            pr=42,
                            login="tidepool-bot",
                        ),
                    ),
                ),
                files=(f"{self.root}/state/ledger/2026-10.jsonl",),
                skipped=(),
            ),
        )

    def test_should_refuse_a_pull_request_no_task_opened(self):
        # Arrange
        self.verdict.write_text(json.dumps(PASS), encoding="utf-8")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pr=41, file=str(self.verdict)), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no task.pr_opened of @PROJECT.tidepool names the pull request #41")

    def test_should_refuse_a_verdict_naming_no_pull_request_on_a_project_with_a_forge(self):
        # Arrange
        self.verdict.write_text(json.dumps(PASS), encoding="utf-8")
        no_pull_request = None

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pr=no_pull_request, file=str(self.verdict)), self.runtime)

        # Assert
        self.assertEqual(
            str(raised.exception), "@PROJECT.tidepool acts through the forge github: the verdict names its pull request"
        )

    def test_should_give_the_recorded_verdict_of_the_task_of_the_pull_request(self):
        # Arrange
        self.verdict.write_text(json.dumps(PASS), encoding="utf-8")

        # Act
        document = COMMAND.run(Namespace(pr=42, file=str(self.verdict)), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "T7",
                "pr": 42,
                "head": "8885daa",
                "verdict": "pass",
                "findings": [],
                "login": None,
            },
        )


LOCAL_PROJECT = (("PATH", "/home/user/tidepool"), ("MAIN", "main"), ("FORGE", "none"))
LOCAL_TASK_WORKTREE = {
    **TASK_WORKTREE,
    ("git", "branch", "--show-current"): "feature/T7-tide-table\n",
    ("git", "rev-parse", "HEAD"): "8885daa\n",
}


class VerifyVerdictOfATaskWithoutAForgeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED])
        self.verdict = self.root / "verdict.json"
        corpus = {"PROJECT": {"tidepool": LOCAL_PROJECT}, "TASK": {"T7": ()}, "POLICY": {}}
        self.runtime = create_test_runtime(
            create_test_paths(self.root), run_process=create_machine_double(corpus, LOCAL_TASK_WORKTREE)
        )
        self.no_pull_request = None

    def test_should_record_the_verdict_of_the_head_of_the_task_branch_with_no_pull_request(self):
        # Arrange
        self.verdict.write_text(json.dumps(PASS), encoding="utf-8")

        # Act
        COMMAND.run(Namespace(pr=self.no_pull_request, file=str(self.verdict)), self.runtime)

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries[-1],
            LedgerEntry(
                instant=datetime(2026, 10, 19, 9, 0, tzinfo=UTC),
                event=TaskVerdict(
                    project="tidepool",
                    wave="tidepool_w16",
                    task="T7",
                    pr=None,
                    head="8885daa",
                    verdict="pass",
                    findings=(),
                    login=None,
                ),
            ),
        )

    def test_should_refuse_a_verdict_of_a_head_no_longer_the_head_of_the_task_branch(self):
        # Arrange
        self.verdict.write_text(json.dumps({**PASS, "head": "4c1d2e0"}), encoding="utf-8")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(pr=self.no_pull_request, file=str(self.verdict)), self.runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "the verdict judged 4c1d2e0, no longer the head of feature/T7-tide-table, now 8885daa",
        )
