import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.require_login_environment import LoginDemand, require_login_environment
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

COMMAND_INSTANT = datetime(2026, 10, 9, 12, 30, tzinfo=UTC)
TOKEN_ENVIRONMENT = {"GH_TOKEN": "token-of-octo-bot"}
NO_TOKEN = None


class ForgeDouble:
    def __init__(self, environments):
        self.environments = list(environments)
        self.requests = []

    def read_login_environment(self, request, runtime):
        self.requests.append(request)
        return {"schema_version": 1, "environment": self.environments.pop(0)}


class RequireLoginEnvironmentTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        paths = create_test_paths(root)
        self.runtime = create_test_runtime(paths, now=COMMAND_INSTANT)
        self.state_root = paths.state_root
        self.waits = []

    def tearDown(self):
        self.root.cleanup()

    def require(self, forge: ForgeDouble, attempts: int = 3):
        demand = LoginDemand(forge=forge, forge_name="github", login="octo-bot", key="verify", attempts=attempts)
        return require_login_environment(demand, self.runtime, self.waits.append)


class RequireLoginEnvironmentWhenGhPrintsTheTokenTest(RequireLoginEnvironmentTestCase):
    def test_should_answer_the_environment_of_the_login(self):
        # Arrange
        forge = ForgeDouble([TOKEN_ENVIRONMENT])

        # Act
        environment = self.require(forge)

        # Assert
        self.assertEqual(environment, {"GH_TOKEN": "token-of-octo-bot"})

    def test_should_ask_the_forge_for_the_login_once(self):
        # Arrange
        forge = ForgeDouble([TOKEN_ENVIRONMENT])

        # Act
        self.require(forge)

        # Assert
        self.assertEqual(forge.requests, [{"schema_version": 1, "login": "octo-bot"}])


class RequireLoginEnvironmentWhenGhPrintsTheTokenAtTheLastAttemptTest(RequireLoginEnvironmentTestCase):
    def test_should_wait_a_delay_doubling_from_one_second_between_the_attempts(self):
        # Arrange
        forge = ForgeDouble([NO_TOKEN, NO_TOKEN, TOKEN_ENVIRONMENT])

        # Act
        environment = self.require(forge)

        # Assert
        self.assertEqual(self.waits, [1.0, 2.0])
        self.assertEqual(environment, {"GH_TOKEN": "token-of-octo-bot"})


class RequireLoginEnvironmentWhenGhNeverPrintsTheTokenTest(RequireLoginEnvironmentTestCase):
    def setUp(self):
        super().setUp()
        self.forge = ForgeDouble([NO_TOKEN, NO_TOKEN, NO_TOKEN])

    def test_should_stop_on_an_error_naming_the_login_and_the_attempts(self):
        # Arrange
        rows = [
            (1, "gh printed no token for the login octo-bot, bound to verify, after 1 attempt"),
            (3, "gh printed no token for the login octo-bot, bound to verify, after 3 attempts"),
        ]
        for attempts, expected in rows:
            with self.subTest(attempts=attempts):
                # Arrange
                forge = ForgeDouble([NO_TOKEN, NO_TOKEN, NO_TOKEN])

                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    self.require(forge, attempts)

                # Assert
                self.assertEqual(str(refusal.exception), expected)

    def test_should_wait_after_every_attempt_but_the_last(self):
        # Act
        with self.assertRaises(BrigadeError):
            self.require(self.forge)

        # Assert
        self.assertEqual(self.waits, [1.0, 2.0])

    def test_should_record_the_login_unavailable_in_the_ledger(self):
        # Act
        with self.assertRaises(BrigadeError):
            self.require(self.forge)

        # Assert
        line = (self.state_root / "ledger" / "2026-10.jsonl").read_text()
        self.assertEqual(
            json.loads(line),
            {
                "schema_version": 1,
                "ts": "2026-10-09T12:30:00Z",
                "event": "forge_account.unavailable",
                "login": "octo-bot",
                "key": "verify",
            },
        )
