import unittest

from brigade.checks.forge_logins import check
from tests.unit.create_test_runtime import create_test_runtime


def create_subject(logins: list) -> dict:
    return {
        "schema_version": 1,
        "project": "/srv/shop",
        "parameters": {},
        "collected": {"forge-logins": {"summary": {"logins": logins}, "items": []}},
    }


class ForgeLoginsCheckTest(unittest.TestCase):
    def test_should_fail_naming_each_login_gh_prints_no_token_for(self):
        # Arrange
        subject = create_subject(
            [
                {"login": "clauche-bot", "keys": ["build", "cli"], "token": True},
                {"login": "prudence-bot", "keys": ["review"], "token": False},
            ]
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "forge_logins",
                "verdict": "fail",
                "findings": ["gh printed no token for the login prudence-bot, bound to review"],
            },
        )

    def test_should_pass_once_every_login_prints_its_token(self):
        # Arrange
        subject = create_subject([{"login": "clauche-bot", "keys": ["build", "cli"], "token": True}])

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(document, {"schema_version": 1, "name": "forge_logins", "verdict": "pass", "findings": []})
