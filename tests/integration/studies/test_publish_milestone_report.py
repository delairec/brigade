from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.convert_study import Study
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.publish_milestone_report import publish_milestone_report
from brigade.studies.study_run_context import StudyRunContext
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.integration.repository_test_case import RepositoryTestCase
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment
from tests.unit.studies.test_publish_milestone_report import create_forge

RUN_ID = "20261108T170002Z-0a1e3b"
BRANCH = "integration/hardening"
MILESTONES_PATH = "corpus/milestones.awawa"
MILESTONE_M6_ACTIVE = 'MILESTONE M6\n\tTITLE "Hardening"\n\tSTATUS active\n'
STUDY = Study(
    name="milestone-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    milestone=MilestoneReportOrder(project="oak", milestone="M6", branch=BRANCH, waves=("oak_w2",), tasks=("B17",)),
)


class DocumentDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"entities": [{"type": "REPORT", "name": "oak_M6", "fields": [{"name": "MILESTONE", "value": "M6"}]}]}


class RealGitAndScriptedAwawaDouble:
    def __init__(self, scripted: ScriptedProcesses):
        self._scripted = scripted

    def __call__(self, request: ProcessRequest) -> ProcessRecord:
        if request.argv[0] == "git":
            return run_process_without_trail(request)
        return self._scripted(request)


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class PublishMilestoneReportTest(RepositoryTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name)
        self.remote = root / "remote.git"
        self.held_worktree = root / "held"
        self.run_directory = root / "state" / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)
        self.checkout = self.run_directory / "checkout"
        self.cut_milestone_branch()
        write_operational_corpus(root)
        scripted = ScriptedProcesses()
        self.script_awawa(scripted)
        self.runtime = create_test_runtime(create_test_paths(root), run_process=RealGitAndScriptedAwawaDouble(scripted))
        self.script_project(scripted)

    def cut_milestone_branch(self) -> None:
        run_git(self.repository, "config", "user.name", "Ada Lovelace")
        run_git(self.repository, "config", "user.email", "ada@example.org")
        run_git(self.repository, "init", "--quiet", "--bare", str(self.remote))
        run_git(self.repository, "remote", "add", "origin", str(self.remote))
        run_git(self.repository, "switch", "--quiet", "--create", BRANCH)
        (self.repository / "corpus").mkdir()
        (self.repository / MILESTONES_PATH).write_text(MILESTONE_M6_ACTIVE, encoding="utf-8")
        run_git(self.repository, "add", MILESTONES_PATH)
        run_git(self.repository, "commit", "--quiet", "-m", "feat: cut the branch of the milestone")
        run_git(self.repository, "push", "--quiet", "origin", BRANCH)
        run_git(self.repository, "switch", "--quiet", "main")

    def script_awawa(self, scripted: ScriptedProcesses) -> None:
        scripted.answer_json(
            ("awawa", "show", "@MILESTONE.M6", "--json", str(self.checkout)),
            {
                "file": str(self.checkout / MILESTONES_PATH),
                "fields": [
                    {"name": "TITLE", "atoms": ['"Hardening"']},
                    {"name": "SUBJECT", "atoms": ['"harden the tick against moved heads"']},
                    {"name": "STATUS", "atoms": ['"reached"']},
                ],
            },
        )
        scripted.answer_entities(
            self.checkout,
            "TASK",
            {"B17": (("TYPE", "feat"), ("COMPONENT", "tick"), ("MILESTONE", "@MILESTONE.M6"))},
            ("STATUS==implemented",),
        )
        scripted.answer(("awawa", "fmt", str(self.checkout / MILESTONES_PATH)))
        scripted.answer(("awawa", "lint", "--strict", str(self.checkout)))

    def script_project(self, scripted: ScriptedProcesses) -> None:
        scripted.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", str(self.repository)), ("FORGE", "github"), ("CORPUS", "corpus"), ("MAIN", "main"))},
        )

    def create_context(self) -> StudyRunContext:
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(
                configuration=Configuration(), forge=None, forge_name="github", resolve_client=None
            ),
            document=DocumentDouble(),
            resolve_forge={"github": create_forge()}.__getitem__,
        )
        return StudyRunContext(
            runtime=self.runtime, study=STUDY, run_id=RUN_ID, run_directory=self.run_directory, equipment=equipment
        )

    def read_forge_subjects(self) -> list[str]:
        return run_git(self.remote, "log", "--format=%s", BRANCH).splitlines()

    def test_should_publish_the_report_and_the_reached_milestone_on_a_branch_another_worktree_holds(self):
        # Arrange
        run_git(self.repository, "worktree", "add", "--quiet", str(self.held_worktree), BRANCH)

        # Act
        publish_milestone_report(self.create_context())

        # Assert
        self.assertEqual(
            self.read_forge_subjects(),
            [
                "docs(corpus): mark @MILESTONE.M6 reached",
                "docs(milestones): add the report of M6",
                "feat: cut the branch of the milestone",
                "first",
            ],
        )

    def test_should_leave_the_branch_another_worktree_holds_where_it_stands(self):
        # Arrange
        run_git(self.repository, "worktree", "add", "--quiet", str(self.held_worktree), BRANCH)
        held_head = run_git(self.repository, "rev-parse", BRANCH)

        # Act
        publish_milestone_report(self.create_context())

        # Assert
        self.assertEqual(run_git(self.repository, "rev-parse", BRANCH), held_head)
        self.assertEqual(run_git(self.held_worktree, "rev-parse", "HEAD"), held_head)

    def test_should_bring_the_local_branch_along_when_no_worktree_holds_it(self):
        # Act
        publish_milestone_report(self.create_context())

        # Assert
        self.assertEqual(run_git(self.repository, "rev-parse", BRANCH), run_git(self.remote, "rev-parse", BRANCH))

    def test_should_publish_over_the_checkout_an_interrupted_attempt_left_behind(self):
        # Arrange
        run_git(self.repository, "worktree", "add", "--quiet", "--detach", str(self.checkout), f"origin/{BRANCH}")
        (self.checkout / "half-written.md").write_text("left by the attempt\n", encoding="utf-8")

        # Act
        publish_milestone_report(self.create_context())

        # Assert
        self.assertEqual(self.read_forge_subjects()[0], "docs(corpus): mark @MILESTONE.M6 reached")
