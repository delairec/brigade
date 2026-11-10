import contextlib
import io
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.system.parse_configuration import Configuration
from brigade.waves.list_candidate_waves import CandidateWave, list_candidate_waves
from brigade.waves.read_project_tasks import ProjectTasksReading, read_project_tasks
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

REPOSITORY = "/srv/shop"
MAIN_SHA = "4f1c2a9"
MILESTONE_SHA = "7d3e1b0"
MILESTONE_BRANCH = "integration/milestone-integration-branch"
ACTIVE_MILESTONES = ("awawa", "status", "MILESTONE", "--where", "STATUS==active", "--json")
PROJECT = Entity(
    name="shop",
    fields=(
        EntityField(name="PATH", value=REPOSITORY),
        EntityField(name="MAIN", value="main"),
        EntityField(name="FORGE", value="none"),
    ),
)
CUT_OF_M9 = LedgerEntry(
    instant=datetime(2026, 10, 29, 9, 0, tzinfo=UTC),
    event=MilestoneBranchCut(project="shop", milestone="M9", branch=MILESTONE_BRANCH, login=None),
)
WAVE_HOLDING_S3 = LedgerEntry(
    instant=datetime(2026, 10, 29, 10, 0, tzinfo=UTC),
    event=WaveStarted(wave="shop_w4", project="shop", branch="integration/shop_w4", tasks=("S3",)),
)
DIGEST_OF_S3_AT_MAIN = "21b807323b879dff2247378dd129efd4c59248cf48c93498e31ce3e7709eca31"
WAVE_PARKING_S3_ON_A_QUESTION = (
    LedgerEntry(
        instant=datetime(2026, 10, 29, 10, 0, tzinfo=UTC),
        event=WaveStarted(wave="shop_w3", project="shop", tasks=("S3",), task_digests={"S3": DIGEST_OF_S3_AT_MAIN}),
    ),
    LedgerEntry(
        instant=datetime(2026, 10, 29, 10, 30, tzinfo=UTC),
        event=TaskParked(wave="shop_w3", task="S3", reason="run r1 blocked: Which forge?", blockers=()),
    ),
    LedgerEntry(instant=datetime(2026, 10, 29, 10, 30, tzinfo=UTC), event=WaveClosed(wave="shop_w3")),
)
TASKS_AT_MAIN = {
    "S1": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9")),
    "S2": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9"), ("AFTER", "@TASK.S1")),
    "S3": (("STATUS", "todo"),),
    "S4": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M10")),
    "S5": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M11")),
    "S6": (("STATUS", "draft"), ("MILESTONE", "@MILESTONE.M12")),
}
NO_MILESTONE = None
TASKS_NAMING_NO_MILESTONE = {"S3": (("STATUS", "todo"),)}
S1_IMPLEMENTED_ON_THE_MILESTONE_BRANCH = {
    "S1": (("STATUS", "implemented"), ("MILESTONE", "@MILESTONE.M9")),
    "S2": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9"), ("AFTER", "@TASK.S1")),
}
S1_IMPLEMENTED_NOWHERE = {
    "S1": (("STATUS", "draft"), ("MILESTONE", "@MILESTONE.M9")),
    "S2": (("STATUS", "todo"), ("MILESTONE", "@MILESTONE.M9"), ("AFTER", "@TASK.S1")),
}
ACTIVE_AT_MAIN = {"entities": [{"type": "MILESTONE", "name": name} for name in ("M9", "M10", "M12", "M13")]}
NO_INCOMING_REFERENCE = {"incoming": []}


class ListCandidateWavesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.processes.answer_entities(
            self.root / "config", "PROJECT", {"shop": (("PATH", REPOSITORY), ("MAIN", "main"), ("FORGE", "none"))}
        )
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.main_tree = self.answer_tree("main", MAIN_SHA, TASKS_AT_MAIN)
        self.processes.answer_json((*ACTIVE_MILESTONES, str(self.main_tree)), ACTIVE_AT_MAIN)

    def answer_tree(self, ref: str, sha: str, tasks: dict) -> Path:
        tree = self.root / "cache" / "refs" / "shop" / sha
        tree.mkdir(parents=True, exist_ok=True)
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"), stdout=f"{sha}\n"
        )
        self.processes.answer_entities(tree, "TASK", tasks)
        for task in tasks:
            self.processes.answer_json(("awawa", "refs", f"@TASK.{task}", "--json", str(tree)), NO_INCOMING_REFERENCE)
        return tree

    def list_waves(self, *entries: LedgerEntry) -> tuple[CandidateWave, ...]:
        reading = ProjectTasksReading(
            configuration=Configuration(),
            project=PROJECT,
            read_environment=dict,
            entries=(CUT_OF_M9, *entries),
        )
        return list_candidate_waves(self.runtime, reading, read_project_tasks(self.runtime, reading, NO_MILESTONE))


class ListCandidateWavesOfTheActiveMilestonesTest(ListCandidateWavesTestCase):
    def test_should_admit_a_task_whose_after_is_implemented_on_the_milestone_branch_alone(self):
        # Arrange
        self.answer_tree(MILESTONE_BRANCH, MILESTONE_SHA, S1_IMPLEMENTED_ON_THE_MILESTONE_BRANCH)

        # Act
        waves = self.list_waves()

        # Assert
        self.assertEqual(waves[0], CandidateWave(milestone="M9", tasks=("S2",)))

    def test_should_refuse_a_task_whose_after_is_implemented_on_neither_branch(self):
        # Arrange
        self.answer_tree(MILESTONE_BRANCH, MILESTONE_SHA, S1_IMPLEMENTED_NOWHERE)

        # Act
        waves = self.list_waves()

        # Assert
        self.assertEqual(
            waves, (CandidateWave(milestone="M10", tasks=("S4",)), CandidateWave(milestone=None, tasks=("S3",)))
        )

    def test_should_list_one_wave_per_active_milestone_with_a_candidate_then_the_tasks_naming_none(self):
        # Arrange
        self.answer_tree(MILESTONE_BRANCH, MILESTONE_SHA, S1_IMPLEMENTED_ON_THE_MILESTONE_BRANCH)

        # Act
        waves = self.list_waves()

        # Assert
        self.assertEqual(
            waves,
            (
                CandidateWave(milestone="M9", tasks=("S2",)),
                CandidateWave(milestone="M10", tasks=("S4",)),
                CandidateWave(milestone=None, tasks=("S3",)),
            ),
        )

    def test_should_leave_out_a_task_in_an_open_wave(self):
        # Arrange
        self.answer_tree(MILESTONE_BRANCH, MILESTONE_SHA, S1_IMPLEMENTED_ON_THE_MILESTONE_BRANCH)

        # Act
        waves = self.list_waves(WAVE_HOLDING_S3)

        # Assert
        self.assertEqual(
            waves, (CandidateWave(milestone="M9", tasks=("S2",)), CandidateWave(milestone="M10", tasks=("S4",)))
        )


class ListCandidateWavesOfATaskParkedOnAQuestionTest(ListCandidateWavesTestCase):
    def setUp(self):
        super().setUp()
        self.answer_tree(MILESTONE_BRANCH, MILESTONE_SHA, S1_IMPLEMENTED_ON_THE_MILESTONE_BRANCH)

    def list_waves_and_stderr(self, *entries: LedgerEntry) -> tuple[tuple[CandidateWave, ...], str]:
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            waves = self.list_waves(*entries)
        return waves, errors.getvalue()

    def test_should_leave_out_a_task_whose_closed_wave_parked_it_on_the_question_of_its_run(self):
        # Act
        waves, _ = self.list_waves_and_stderr(*WAVE_PARKING_S3_ON_A_QUESTION)

        # Assert
        self.assertEqual(
            waves, (CandidateWave(milestone="M9", tasks=("S2",)), CandidateWave(milestone="M10", tasks=("S4",)))
        )

    def test_should_name_on_stderr_the_task_held_with_its_wave_and_its_question(self):
        # Act
        _, stderr = self.list_waves_and_stderr(*WAVE_PARKING_S3_ON_A_QUESTION)

        # Assert
        self.assertEqual(
            stderr,
            "brigade tick: @TASK.S3 is held since the wave shop_w3: it waits for an answer to: Which forge?\n",
        )

    def test_should_admit_again_the_task_once_its_entity_differs_from_the_one_its_run_read(self):
        # Arrange
        amended_s3 = {"S3": (("STATUS", "todo"), ("SPEC", "the forge is github"))}
        self.answer_tree("main", MAIN_SHA, {**TASKS_AT_MAIN, **amended_s3})

        # Act
        waves, stderr = self.list_waves_and_stderr(*WAVE_PARKING_S3_ON_A_QUESTION)

        # Assert
        self.assertEqual(waves[-1], CandidateWave(milestone=None, tasks=("S3",)))
        self.assertEqual(stderr, "")

    def test_should_admit_again_the_task_queued_again_by_the_requeue(self):
        # Arrange
        requeued = LedgerEntry(
            instant=datetime(2026, 10, 29, 12, 0, tzinfo=UTC),
            event=TaskState(wave="shop_w3", task="S3", state="queued", reason="brigade wave requeue"),
        )

        # Act
        waves, stderr = self.list_waves_and_stderr(*WAVE_PARKING_S3_ON_A_QUESTION, requeued)

        # Assert
        self.assertEqual(waves[-1], CandidateWave(milestone=None, tasks=("S3",)))
        self.assertEqual(stderr, "")

    def test_should_name_nothing_when_no_task_waits_for_an_answer(self):
        # Act
        _, stderr = self.list_waves_and_stderr()

        # Assert
        self.assertEqual(stderr, "")


class ListCandidateWavesOfTasksNamingNoMilestoneTest(ListCandidateWavesTestCase):
    def test_should_read_no_milestone_when_no_task_names_one(self):
        # Arrange
        self.answer_tree("main", MAIN_SHA, TASKS_NAMING_NO_MILESTONE)

        # Act
        self.list_waves()

        # Assert
        self.assertNotIn((*ACTIVE_MILESTONES, str(self.main_tree)), self.processes.list_argvs())


if __name__ == "__main__":
    unittest.main()
