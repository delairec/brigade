import json
from pathlib import Path
from unittest.mock import ANY

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
BROKEN_SPEC = {"grade": "high", "file": "src/cart/button.py", "line": 2, "broken": "SPEC 1 of @TASK.S3"}


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

    def read_verdicts(self) -> list[dict]:
        lines = [
            json.loads(line)
            for month in sorted((self.state / "ledger").glob("*.jsonl"))
            for line in month.read_text().splitlines()
        ]
        return [line for line in lines if line["event"] == "task.verdict"]


class BrigadeVerifyVerdictUnderTheVerdictModeTest(VerifyVerdictTestCase):
    def test_should_record_the_verdict_on_the_head_of_the_pull_request(self):
        # Act
        completed = self.run_verify_verdict({"head": self.read_head(), "verdict": "changes", "findings": [BROKEN_SPEC]})

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            self.read_verdicts(),
            [
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
                        {"grade": "high", "file": "src/cart/button.py", "line": 2, "broken": "SPEC 1 of @TASK.S3"}
                    ],
                    "login": None,
                }
            ],
        )
