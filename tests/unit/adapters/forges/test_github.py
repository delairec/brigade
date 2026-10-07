import unittest
from unittest import mock

from brigade.adapters.forges.github import describe_account
from brigade.system.run_process import ProcessRecord


def make_runtime(stdout: str, exit_code: int = 0):
    return mock.Mock(
        run_process=lambda request: ProcessRecord(
            argv=request.argv, cwd=request.cwd, exit_code=exit_code, stdout=stdout, stderr=""
        )
    )


class DescribeAccountTest(unittest.TestCase):
    def test_should_read_the_active_login(self):
        # Arrange
        stdout = '{"hosts": {"github.com": [{"login": "ada", "active": true}]}}'

        # Act
        document = describe_account({}, make_runtime(stdout))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "login": "ada"})

    def test_should_return_none_when_no_account_is_active(self):
        # Arrange
        stdout = '{"hosts": {"github.com": [{"login": "ada", "active": false}]}}'

        # Act
        document = describe_account({}, make_runtime(stdout))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "login": None})

    def test_should_return_none_when_gh_fails(self):
        # Act
        document = describe_account({}, make_runtime("", exit_code=1))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "login": None})

    def test_should_return_none_when_the_output_is_not_json(self):
        # Act
        document = describe_account({}, make_runtime("not json"))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "login": None})

    def test_should_skip_an_inactive_account_and_read_the_next_active_one(self):
        # Arrange
        stdout = '{"hosts": {"github.com": [{"login": "ada", "active": false},{"login": "grace", "active": true}]}}'

        # Act
        document = describe_account({}, make_runtime(stdout))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "login": "grace"})
