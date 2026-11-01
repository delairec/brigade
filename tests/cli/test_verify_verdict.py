import json
from pathlib import Path
from unittest.mock import ANY

from tests.cli.read_ledger_events import read_ledger_events
from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_collect import install_executable
from tests.cli.test_verify_preflight import VerifyPreflightTestCase

REVIEWING_GH = (
    "#!/bin/sh\n"
    'printf \'%s\\n\' "$*" >> "{calls}"\n'
    'case "$1 $2" in\n'
    '  "auth token") echo "token-of-$6" ;;\n'
    '  "auth status") echo \'{{"hosts": {{"github.com": [{{"login": "review-bot", "active": true}}]}}}}\' ;;\n'
    '  "pr view") cat "{pull_request}" ;;\n'
    "esac\n"
)
BROKEN_SPEC = {
    "grade": "high",
    "file": "src/cart/button.py",
    "line": 2,
    "broken": "SPEC 1 of @TASK.S3",
    "summary": "the button empties no cart",
}


class VerifyVerdictTestCase(VerifyPreflightTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name).resolve()
        install_executable(
            root / "tools" / "gh", REVIEWING_GH.format(calls=self.gh_calls, pull_request=self.pull_request)
        )
        self.verdict = root / "verdict.json"

    def run_verify_verdict(self, verdict: dict):
        self.verdict.write_text(json.dumps(verdict))
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "verify",
            "verdict",
            "42",
            "--file",
            str(self.verdict),
            environment=self.describe_environment(),
            cwd=self.project.path,
        )

    def read_events(self) -> list[dict]:
        return read_ledger_events(self.state / "ledger")


class BrigadeVerifyVerdictUnderTheVerdictModeTest(VerifyVerdictTestCase):
    def test_should_record_the_verdict_on_the_head_of_the_pull_request(self):
        # Act
        completed = self.run_verify_verdict({"head": self.read_head(), "verdict": "changes", "findings": [BROKEN_SPEC]})

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-17T09:00:00Z",
                    "event": "wave.started",
                    "wave": "shop_w1",
                    "project": "shop",
                    "branch": "integration/M1-empty-cart",
                    "tasks": ["S3"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-17T12:00:00Z",
                    "event": "task.pr_opened",
                    "project": "shop",
                    "task": "S3",
                    "wave": "shop_w1",
                    "branch": "task/M1-empty-cart/S3",
                    "pr": 42,
                    "login": "octo-bot",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.verdict",
                    "project": "shop",
                    "wave": "shop_w1",
                    "task": "S3",
                    "pr": 42,
                    "head": self.read_head(),
                    "verdict": "changes",
                    "findings": [
                        {
                            "grade": "high",
                            "file": "src/cart/button.py",
                            "line": 2,
                            "broken": "SPEC 1 of @TASK.S3",
                            "summary": "the button empties no cart",
                        }
                    ],
                    "login": None,
                },
            ],
        )
