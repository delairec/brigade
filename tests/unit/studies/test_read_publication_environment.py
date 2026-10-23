import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.convert_study import Study
from brigade.studies.locate_study_project import StudyProject
from brigade.studies.read_publication_environment import read_publication_environment
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.parse_configuration import Configuration
from brigade.system.require_login_environment import LoginUnavailable
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

STUDY = Study(
    name="trees",
    project="oak",
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="issue",
    answer_type="FINDING",
    status="active",
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

GITHUB_PROJECT = StudyProject(path=Path("/srv/oak"), forge="github")
PROJECT_WITHOUT_FORGE = StudyProject(path=Path("/srv/oak"), forge=None)
CLI_BOUND_TO_OCTO_CLI = Configuration(forge_accounts={"cli": "octo-cli"}, forge_attempts=1)
NOTHING_BOUND = Configuration()


class ForgeDouble:
    def __init__(self, environments: dict):
        self._environments = environments

    def read_login_environment(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "environment": self._environments.get(request["login"])}


class ReadPublicationEnvironmentTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=ScriptedProcesses())

    def create_context(self, configuration: Configuration, forge: ForgeDouble) -> StudyRunContext:
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(configuration=configuration, forge=None, forge_name="github"),
            resolve_forge={"github": forge}.__getitem__,
        )
        return StudyRunContext(
            runtime=self.runtime, study=STUDY, run_id="1", run_directory=Path("/run"), equipment=equipment
        )

    def test_should_answer_the_environment_of_the_login_bound_to_cli(self):
        # Arrange
        context = self.create_context(CLI_BOUND_TO_OCTO_CLI, ForgeDouble({"octo-cli": {"GH_TOKEN": "cli-token"}}))

        # Act
        environment = read_publication_environment(context, GITHUB_PROJECT)

        # Assert
        self.assertEqual(environment, {"GH_TOKEN": "cli-token"})

    def test_should_answer_the_environment_of_brigade_itself_with_no_login_bound_to_cli(self):
        # Arrange
        context = self.create_context(NOTHING_BOUND, ForgeDouble({"octo-cli": {"GH_TOKEN": "cli-token"}}))

        # Act
        environment = read_publication_environment(context, GITHUB_PROJECT)

        # Assert
        self.assertEqual(environment, {})

    def test_should_answer_the_environment_of_brigade_itself_for_a_project_without_a_forge(self):
        # Arrange
        context = self.create_context(CLI_BOUND_TO_OCTO_CLI, ForgeDouble({"octo-cli": {"GH_TOKEN": "cli-token"}}))

        # Act
        environment = read_publication_environment(context, PROJECT_WITHOUT_FORGE)

        # Assert
        self.assertEqual(environment, {})

    def test_should_refuse_a_login_bound_to_cli_for_which_gh_prints_no_token(self):
        # Arrange
        context = self.create_context(CLI_BOUND_TO_OCTO_CLI, ForgeDouble({}))

        # Act
        with self.assertRaises(LoginUnavailable) as refusal:
            read_publication_environment(context, GITHUB_PROJECT)

        # Assert
        self.assertEqual(
            str(refusal.exception), "gh printed no token for the login octo-cli, bound to cli, after 1 attempt"
        )
