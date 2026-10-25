import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_job_steps import JobStepsQuery, ask_job_steps
from tests.unit.forge_double import ForgeDouble

NO_RUNTIME_NEEDED = None
JOB_LINK = "https://github.com/octo/shop/actions/runs/7/job/70"
QUERY = JobStepsQuery(repository="/projects/shop", link=JOB_LINK, environment={"GH_TOKEN": "token-of-octo-cli"})


class AskJobStepsTest(unittest.TestCase):
    def test_should_refuse_an_answer_whose_step_is_not_an_object_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"read_job_steps": lambda request: {"schema_version": 1, "steps": ["Run tests"]}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_job_steps(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered read_job_steps: steps[0] is a string, not an object"
        )

    def test_should_answer_the_steps_the_forge_reads(self):
        # Arrange
        step = {"name": "Run tests", "conclusion": "failure"}
        forge = ForgeDouble({"read_job_steps": lambda request: {"schema_version": 1, "steps": [step]}})

        # Act
        steps = ask_job_steps(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(steps, [{"name": "Run tests", "conclusion": "failure"}])

    def test_should_answer_no_steps_when_the_link_names_no_job(self):
        # Arrange
        no_job = None
        forge = ForgeDouble({"read_job_steps": lambda request: {"schema_version": 1, "steps": no_job}})

        # Act
        steps = ask_job_steps(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertIsNone(steps)

    def test_should_ask_the_forge_for_the_steps_of_the_job_the_link_names(self):
        # Arrange
        forge = ForgeDouble({"read_job_steps": lambda request: {"schema_version": 1, "steps": []}})

        # Act
        ask_job_steps(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.list_requests("read_job_steps"),
            [
                {
                    "schema_version": 1,
                    "repository": "/projects/shop",
                    "link": "https://github.com/octo/shop/actions/runs/7/job/70",
                    "environment": {"GH_TOKEN": "token-of-octo-cli"},
                }
            ],
        )
