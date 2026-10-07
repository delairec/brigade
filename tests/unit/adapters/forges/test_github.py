import unittest
from types import SimpleNamespace

from brigade.adapters.forges.github import describe_account
from brigade.system.run_process import ProcessRecord

DESCRIBE_REQUEST = {"schema_version": 1}


def create_runtime(hosts_document: str) -> SimpleNamespace:
    def run_gh(request):
        return ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=0, stdout=hosts_document, stderr="", duration_ms=0
        )

    return SimpleNamespace(run_process=run_gh)


class DescribeAccountTest(unittest.TestCase):
    def test_should_name_the_active_account_after_an_inactive_one(self):
        # Arrange
        runtime = create_runtime(
            '{"hosts": {"github.com": [{"login": "ada", "active": false}, {"login": "Clauche-bot", "active": true}]}}'
        )

        # Act
        account = describe_account(DESCRIBE_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": "Clauche-bot"})

    def test_should_name_no_account_when_none_is_active(self):
        # Arrange
        runtime = create_runtime('{"hosts": {"github.com": [{"login": "ada", "active": false}]}}')

        # Act
        account = describe_account(DESCRIBE_REQUEST, runtime)

        # Assert
        self.assertEqual(account, {"schema_version": 1, "login": None})
