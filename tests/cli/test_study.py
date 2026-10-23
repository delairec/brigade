import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.cli.test_collect import install_executable
from tests.cli.test_tick import WEEKLY_RUN, LiveStudyRunTestCase
from tests.list_entry_names import list_entry_names


def list_other_runs(runs: Path, run_id: str) -> list[str]:
    return [name for name in list_entry_names(runs) if name != run_id]


PINNED_COMMIT_DATES = {"GIT_AUTHOR_DATE": "2026-10-12T09:00:00Z", "GIT_COMMITTER_DATE": "2026-10-12T09:00:00Z"}
QUESTION = "what changed in the shop this week?"


class StudyTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.project = TemporaryProject(
            root / "projects" / "shop", {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}
        )
        self.project.write("README.md", "shop\n")
        self.project.track("README.md")
        self.project.run_git("commit", "--quiet", "-m", "start the shop")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))

    def tearDown(self):
        self.root.cleanup()

    def run_study(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "study", *arguments)

    def read_studies(self) -> str:
        return (self.machine.corpus / "studies.awawa").read_text()


class BrigadeStudyNewTest(StudyTestCase):
    def test_should_record_the_study_with_the_question_verbatim(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved this week",
            "--question",
            QUESTION,
            "--project",
            "shop",
            "--collector",
            "git-log since=7d",
            "--collector",
            "shell: ls",
            "--every",
            "daily@09:00",
            "--output",
            "issue",
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_studies(),
            "STUDY weekly\n"
            '\tTITLE "what moved this week"\n'
            '\tQUESTION "what changed in the shop this week?"\n'
            "\tPROJECT @PROJECT.shop\n"
            '\tCOLLECTOR "git-log since=7d"\n'
            '\tCOLLECTOR "shell: ls"\n'
            "\tSLOT report\n"
            '\tEVERY "daily@09:00"\n'
            '\tOUTPUT "issue"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )

    def test_should_commit_the_study(self):
        # Act
        self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--collector",
            "worktrees",
            "--every",
            "daily@09:00",
            "--output",
            "issue",
        )

        # Assert
        self.assertEqual(self.machine.read_git("log", "-1", "--format=%s"), "brigade study new: @STUDY.weekly\n")

    def test_should_record_a_scan_with_no_slot_question_nor_project(self):
        # Act
        completed = self.run_study(
            "new",
            "trees",
            "--title",
            "the worktrees",
            "--collector",
            "worktrees",
            "--slot",
            "none",
            "--every",
            "1h",
            "--output",
            "issue",
            "--answer",
            "ANSWER",
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_studies(),
            "STUDY trees\n"
            '\tTITLE "the worktrees"\n'
            '\tCOLLECTOR "worktrees"\n'
            "\tSLOT none\n"
            '\tEVERY "1h"\n'
            '\tOUTPUT "issue"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )

    def test_should_print_the_study_recorded(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--collector",
            "worktrees",
            "--every",
            "daily@09:00",
            "--output",
            "issue",
        )

        # Assert
        self.assertEqual(completed.stdout, "@STUDY.weekly recorded, every daily@09:00\n")

    def test_should_exit_1_naming_a_schedule_of_another_form(self):
        # Act
        completed = self.run_study(
            "new", "weekly", "--title", "what moved", "--collector", "worktrees", "--every", "1d", "--output", "issue"
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade study new: the schedule 1d is none of <n>m, <n>h, daily@HH:MM or <day>@HH:MM, day mon to sun\n",
        )

    def test_should_exit_1_naming_an_answer_type_the_schema_does_not_declare(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--collector",
            "worktrees",
            "--every",
            "daily@09:00",
            "--output",
            "issue",
            "--answer",
            "VERDICT",
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade study new: the schema of the operational corpus declares no VERDICT\n"
        )

    def test_should_exit_1_naming_a_project_that_is_not_registered(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--project",
            "cart",
            "--collector",
            "worktrees",
            "--every",
            "daily@09:00",
            "--output",
            "issue",
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade study new: @PROJECT.cart is not registered\n")

    def test_should_exit_1_naming_a_shell_command_it_cannot_split(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--collector",
            "shell: printf 'oak",
            "--every",
            "daily@09:00",
            "--output",
            "issue",
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade study new: the command printf 'oak cannot be split into an argv: No closing quotation\n",
        )

    def test_should_exit_1_naming_the_inbox_output_it_refuses_until_the_inbox_has_a_store(self):
        # Act
        completed = self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--collector",
            "worktrees",
            "--every",
            "daily@09:00",
            "--output",
            "inbox",
        )

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade study new: the output inbox is refused: the inbox has no store until @TASK.B22\n"
        )

    def test_should_record_no_study_whose_output_is_the_inbox(self):
        # Act
        self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--collector",
            "worktrees",
            "--every",
            "daily@09:00",
            "--output",
            "inbox",
        )

        # Assert
        self.assertEqual(self.machine.read_git("log", "-1", "--format=%s"), "brigade project add: shop\n")


class StudyRunTestCase(StudyTestCase):
    def setUp(self):
        super().setUp()
        self.runs = self.machine.state_home / "brigade" / "runs"
        self.ledger = self.machine.state_home / "brigade" / "ledger"

    def record_scan(self, collector: str) -> None:
        self.run_study(
            "new",
            "trees",
            "--title",
            "the trees",
            "--project",
            "shop",
            "--collector",
            collector,
            "--slot",
            "none",
            "--every",
            "1h",
            "--output",
            "entity:ANSWER",
        )

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted(self.ledger.glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def read_order_events(self) -> list:
        lines = "".join(path.read_text() for path in sorted(self.ledger.glob("*.jsonl"))).splitlines()
        return [
            (event["event"], event.get("step"))
            for event in map(json.loads, lines)
            if event["event"].startswith(("order.", "step."))
        ]


class BrigadeStudyRunTest(StudyRunTestCase):
    def test_should_write_the_result_of_each_step_under_the_run_directory(self):
        # Arrange
        self.record_scan("shell: printf 'oak\\nelm\\n'")

        # Act
        completed = self.run_study("run", "trees", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        steps = self.runs / json.loads(completed.stdout)["run"] / "steps"
        self.assertEqual(list_entry_names(steps), ["collect.json", "judge.json", "output.json"])

    def test_should_record_the_order_and_its_steps_in_the_ledger(self):
        # Arrange
        self.record_scan("shell: printf 'oak\\nelm\\n'")

        # Act
        self.run_study("run", "trees")

        # Assert
        self.assertEqual(
            self.read_order_events(),
            [
                ("order.started", None),
                ("step.done", "collect"),
                ("step.done", "judge"),
                ("step.done", "output"),
                ("order.done", None),
            ],
        )

    def test_should_write_the_answer_holding_the_fields_the_cli_filled_for_a_scan(self):
        # Arrange
        self.record_scan("shell: printf 'oak\\nelm\\n'")

        # Act
        completed = self.run_study("run", "trees", "--json")

        # Assert
        run_id = json.loads(completed.stdout)["run"]
        document = self.runs / run_id / "collectors" / "1" / "collect" / "shell" / "document.json"
        self.assertEqual(
            (self.machine.corpus / "answers.awawa").read_text(),
            f"ANSWER trees_{run_id.replace('-', '_')}\n"
            '\tSTUDY "trees"\n'
            f'\tRUN "{run_id}"\n'
            '\tCOLLECTED "shell"\n'
            '\t\tSUMMARY "{\\"lines\\": 2}"\n'
            f'\t\tDOCUMENT "{document}"\n',
        )

    def test_should_park_the_study_on_a_failed_step_with_its_reason(self):
        # Arrange
        self.record_scan("shell: cat flag")

        # Act
        completed = self.run_study("run", "trees", "--json")

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            self.read_order_events(), [("order.started", None), ("step.failed", "collect"), ("order.parked", "collect")]
        )

    def test_should_run_no_collector_of_a_study_holding_a_command_it_cannot_split(self):
        # Arrange
        self.run_study(
            "new",
            "trees",
            "--title",
            "the trees",
            "--project",
            "shop",
            "--collector",
            "shell: touch ran",
            "--collector",
            "shell: printf oak",
            "--slot",
            "none",
            "--every",
            "1h",
            "--output",
            "entity:ANSWER",
        )
        (self.machine.corpus / "studies.awawa").write_text(
            self.read_studies().replace('"shell: printf oak"', '"shell: printf \'oak"')
        )

        # Act
        self.run_study("run", "trees")

        # Assert
        self.assertCountEqual(
            self.project.path.iterdir(), [self.project.path / ".git", self.project.path / "README.md"]
        )

    def record_scan_whose_output_became_the_inbox(self, collector: str) -> None:
        self.record_scan(collector)
        (self.machine.corpus / "studies.awawa").write_text(
            self.read_studies().replace('OUTPUT "entity:ANSWER"', 'OUTPUT "inbox"')
        )

    def test_should_exit_1_naming_the_inbox_output_of_a_study_recorded_earlier(self):
        # Arrange
        self.record_scan_whose_output_became_the_inbox("shell: printf oak")

        # Act
        completed = self.run_study("run", "trees")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade study run: the output inbox is refused: the inbox has no store until @TASK.B22\n"
        )

    def test_should_run_no_collector_of_a_study_whose_output_is_the_inbox(self):
        # Arrange
        self.record_scan_whose_output_became_the_inbox("shell: touch ran")

        # Act
        self.run_study("run", "trees")

        # Assert
        self.assertCountEqual(
            self.project.path.iterdir(), [self.project.path / ".git", self.project.path / "README.md"]
        )

    def test_should_print_the_step_a_study_parked_at(self):
        # Arrange
        self.record_scan("shell: cat flag")

        # Act
        completed = self.run_study("run", "trees")

        # Assert
        self.assertRegex(completed.stdout, r"^@STUDY\.trees run \d{8}T\d{6}Z-[0-9a-f]{6} parked at collect: ")

    def test_should_resume_a_parked_run_at_its_first_undone_step(self):
        # Arrange
        self.record_scan("shell: cat flag")
        parked = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]
        self.project.write("flag", "raised\n")

        # Act
        completed = self.run_study("run", "trees", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["run"], parked)

    def test_should_run_once_a_study_recorded_with_no_schedule(self):
        # Act
        self.run_study(
            "new",
            "trees",
            "--title",
            "the trees",
            "--collector",
            "shell: true",
            "--slot",
            "none",
            "--output",
            "entity:ANSWER",
        )

        # Assert
        self.assertEqual(self.read_order_events()[-1], ("order.done", None))

    def test_should_print_the_run_of_a_study_recorded_with_no_schedule(self):
        # Act
        completed = self.run_study(
            "new",
            "trees",
            "--title",
            "the trees",
            "--collector",
            "shell: true",
            "--slot",
            "none",
            "--output",
            "entity:ANSWER",
        )

        # Assert
        self.assertRegex(completed.stdout, r"^@STUDY\.trees recorded, run \d{8}T\d{6}Z-[0-9a-f]{6} done\n$")

    def test_should_park_the_study_whose_judging_run_gave_no_answer(self):
        # Arrange
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "reporter.json").write_text(json.dumps(DONE_RESULT))
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\n[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}'
        )
        self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--project",
            "shop",
            "--collector",
            "shell: true",
            "--every",
            "daily@09:00",
            "--output",
            "entity:ANSWER",
        )

        # Act
        completed = self.run_study("run", "weekly", "--json")

        # Assert
        document = json.loads(completed.stdout)
        [judging] = self.read_events("run.finished")
        self.assertEqual(document["state"], "parked")
        self.assertEqual(document["reason"], f"the judging run {judging['run']} gave no answer")
        self.assertEqual(judging["procedure"], "study")

    def test_should_exit_1_naming_a_study_that_is_not_defined(self):
        # Act
        completed = self.run_study("run", "absent")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade study run: @STUDY.absent is not defined in the operational corpus\n"
        )


class BrigadeStudyRunWhileARunOfTheStudyIsLiveTest(LiveStudyRunTestCase):
    def test_should_exit_1_naming_the_live_run_and_start_no_second_run(self):
        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "study", "run", "weekly")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, f"brigade study run: @STUDY.weekly is running in run {WEEKLY_RUN}\n")
        self.assertEqual(self.read_order_events("weekly"), [("order.started", None)])

    def test_should_run_another_study(self):
        # Arrange
        self.record_study("trees", slot="none")

        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "study", "run", "trees")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)


class BrigadeRunsPruneOfStudyRunsTest(StudyRunTestCase):
    def test_should_remove_a_done_study_run_settled_before_the_day(self):
        # Arrange
        self.record_scan("shell: true")
        done = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]

        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "runs", "prune", "--before", "2099-01-01")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, f"removed {done} (finished)\n", completed.stderr)

    def test_should_spare_a_parked_study_run_the_next_study_run_resumes(self):
        # Arrange
        self.record_scan("shell: cat flag")
        parked = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]

        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "runs", "prune", "--before", "2099-01-01")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "no run removed\n", completed.stderr)
        self.assertEqual(list_entry_names(self.runs), [parked])


class BrigadeStudyContextTest(StudyRunTestCase):
    def setUp(self):
        super().setUp()
        self.run_study(
            "new",
            "trees",
            "--title",
            "the trees",
            "--question",
            QUESTION,
            "--project",
            "shop",
            "--collector",
            "shell: printf 'oak\\nelm\\n'",
            "--slot",
            "none",
            "--every",
            "1h",
            "--output",
            "entity:ANSWER",
        )
        self.run_id = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]
        self.document = self.runs / self.run_id / "collectors" / "1" / "collect" / "shell" / "document.json"

    def test_should_present_the_question_and_the_evidence_of_each_collector(self):
        # Act
        completed = self.run_study("context", self.run_id, "--json")

        # Assert
        package = json.loads(completed.stdout)
        self.assertEqual(package["question"], QUESTION, completed.stderr)
        self.assertEqual(
            package["collected"],
            [{"collector": "shell", "summary": {"lines": 2}, "document": str(self.document)}],
            completed.stderr,
        )

    def test_should_present_the_answer_holding_the_fields_the_cli_filled(self):
        # Act
        completed = self.run_study("context", self.run_id, "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["answer"],
            f"ANSWER trees_{self.run_id.replace('-', '_')}\n"
            '\tSTUDY "trees"\n'
            f'\tRUN "{self.run_id}"\n'
            '\tCOLLECTED "shell"\n'
            '\t\tSUMMARY "{\\"lines\\": 2}"\n'
            f'\t\tDOCUMENT "{self.document}"\n',
            completed.stderr,
        )

    def test_should_name_the_prose_fields_left_to_the_slot(self):
        # Act
        completed = self.run_study("context", self.run_id, "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["prose_fields"], ["NARRATIVE", "FINDING"], completed.stderr)

    def test_should_present_the_schema_of_the_answer_type(self):
        # Act
        completed = self.run_study("context", self.run_id, "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["schema"],
            "SCHEMA ANSWER\n"
            '\tDESC "the answer of one run of a study: the CLI fills what the collectors gave, the judging"\n'
            '\t\t+ "slot the prose"\n'
            "\tFIELD STUDY string\n"
            "\t\tREQUIRED\n"
            '\t\tDESC "the name of the STUDY answered"\n'
            "\tFIELD RUN string\n"
            "\t\tREQUIRED\n"
            '\t\tDESC "the run of the study"\n'
            "\tFIELD COLLECTED string\n"
            "\t\tREPEATABLE\n"
            '\t\tDESC "one per collector, its name, filled by the CLI"\n'
            "\t\tFIELD SUMMARY string\n"
            "\t\t\tREQUIRED\n"
            '\t\t\tDESC "the summary of its document, as JSON"\n'
            "\t\tFIELD DOCUMENT string\n"
            "\t\t\tREQUIRED\n"
            '\t\t\tDESC "the path of its full document"\n'
            "\tFIELD NARRATIVE string\n"
            "\t\tREPEATABLE\n"
            '\t\tDESC "filled by the judging slot"\n'
            "\tFIELD FINDING string\n"
            "\t\tREPEATABLE\n"
            '\t\tDESC "one finding with its evidence, filled by the judging slot"\n',
            completed.stderr,
        )

    def test_should_write_the_package_to_the_run_directory(self):
        # Act
        completed = self.run_study("context", self.run_id, "--json")

        # Assert
        self.assertEqual(
            json.loads((self.runs / self.run_id / "context.json").read_text()),
            json.loads(completed.stdout),
            completed.stderr,
        )

    def test_should_print_the_question_the_evidence_and_the_prose_fields(self):
        # Act
        completed = self.run_study("context", self.run_id)

        # Assert
        self.assertEqual(
            completed.stdout.split("\n\n")[0],
            f"question: {QUESTION}\n"
            f'shell: {{"lines": 2}}, {self.document}\n'
            "prose fields left to the slot: NARRATIVE, FINDING",
            completed.stderr,
        )

    def test_should_exit_1_naming_a_run_that_is_not_a_study_run(self):
        # Act
        completed = self.run_study("context", "20261015T000000Z-000000")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade study context: 20261015T000000Z-000000 is not a run of a study\n")

    def test_should_exit_1_naming_a_run_parked_before_its_evidence_was_collected(self):
        # Arrange
        self.run_study(
            "new",
            "flags",
            "--title",
            "the flags",
            "--project",
            "shop",
            "--collector",
            "shell: cat flag",
            "--slot",
            "none",
            "--output",
            "entity:ANSWER",
        )
        [parked] = list_other_runs(self.runs, self.run_id)

        # Act
        completed = self.run_study("context", parked)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, f"brigade study context: the run {parked} has collected no evidence yet\n")


class BrigadeStudyAnswerTest(StudyRunTestCase):
    def setUp(self):
        super().setUp()
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "reporter.json").write_text(json.dumps(DONE_RESULT))
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\n[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}'
        )
        self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved",
            "--project",
            "shop",
            "--collector",
            "shell: true",
            "--every",
            "daily@09:00",
            "--output",
            "entity:ANSWER",
        )
        self.run_id = json.loads(self.run_study("run", "weekly", "--json").stdout)["run"]
        self.document = self.runs / self.run_id / "collectors" / "1" / "collect" / "shell" / "document.json"
        self.answer_file = Path(self.root.name) / "answer.awawa"

    def write_answer(self, summary: str, prose: str) -> None:
        self.answer_file.write_text(
            f"ANSWER weekly_{self.run_id.replace('-', '_')}\n"
            '\tSTUDY "weekly"\n'
            f'\tRUN "{self.run_id}"\n'
            '\tCOLLECTED "shell"\n'
            f"\t\tSUMMARY {summary}\n"
            f'\t\tDOCUMENT "{self.document}"\n'
            f"{prose}"
        )

    def test_should_record_an_answer_the_schema_of_its_type_accepts(self):
        # Arrange
        self.write_answer('"{\\"lines\\": 0}"', '\tNARRATIVE "nothing moved"\n')

        # Act
        completed = self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            (self.runs / self.run_id / "answer.awawa").read_text(), self.answer_file.read_text(), completed.stderr
        )

    def test_should_refuse_an_answer_the_schema_of_its_type_rejects(self):
        # Arrange
        self.write_answer('"{\\"lines\\": 0}"', '\tVERDICT "nothing moved"\n')

        # Act
        completed = self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertRegex(completed.stderr, r"^brigade study answer: the schema of ANSWER rejects the answer\n")

    def test_should_refuse_an_answer_that_changed_a_field_the_cli_filled(self):
        # Arrange
        self.write_answer('"{\\"lines\\": 3}"', '\tNARRATIVE "three lines moved"\n')

        # Act
        completed = self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade study answer: the answer changed COLLECTED, a field brigade filled\n"
        )

    def test_should_keep_no_answer_it_refused(self):
        # Arrange
        self.write_answer('"{\\"lines\\": 3}"', '\tNARRATIVE "three lines moved"\n')

        # Act
        self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(list((self.runs / self.run_id).glob("*.awawa")), [])

    def test_should_refuse_an_answer_that_names_another_entity(self):
        # Arrange
        self.answer_file.write_text('ANSWER elsewhere\n\tSTUDY "weekly"\n\tRUN "elsewhere"\n')

        # Act
        completed = self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade study answer: the answer holds no @ANSWER.weekly_{self.run_id.replace('-', '_')}\n",
        )

    def test_should_exit_1_naming_an_answer_file_it_cannot_read(self):
        # Act
        completed = self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, f"brigade study answer: cannot read {self.answer_file}: No such file or directory\n"
        )

    def test_should_finish_a_study_parked_at_its_judging_run_once_its_answer_is_recorded(self):
        # Arrange
        self.write_answer('"{\\"lines\\": 0}"', '\tNARRATIVE "nothing moved"\n')
        self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Act
        completed = self.run_study("run", "weekly", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["state"], "done", completed.stderr)


FAKE_GH = '#!/bin/sh\nprintf \'%s\\n\' "$*" >> "{calls}"\ncat >> "{calls}"\necho https://github.com/acme/atelier/7\n'
REFUSING_GH = '#!/bin/sh\n[ -f "{flag}" ] || exit 1\necho https://github.com/acme/atelier/7\n'
RECEIVING_OUTPUT = '#!/bin/sh\ncat > "{received}"\n'
FORGE_URL = "https://github.com/acme/atelier.git"


class StudyOutputTestCase(StudyRunTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name).resolve()
        self.gh_calls = root / "gh-calls"
        self.received = root / "received.json"
        self.tools = root / "tools"
        install_executable(self.tools / "gh", FAKE_GH.format(calls=self.gh_calls))
        self.environment = {
            **self.machine.describe_environment(),
            "PATH": f"{self.tools}{os.pathsep}{self.machine.search_path}",
        }

    def add_forge_project(self) -> TemporaryProject:
        root = Path(self.root.name).resolve()
        environment = {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}
        remote = TemporaryProject(root / "remotes" / "atelier", environment)
        with (self.machine.home / ".gitconfig").open("a") as configuration:
            configuration.write(f'[url "{remote.path}"]\n\tpushInsteadOf = {FORGE_URL}\n')
        atelier = TemporaryProject(root / "projects" / "atelier", environment)
        atelier.write("README.md", "atelier\n")
        atelier.track("README.md")
        atelier.run_git("commit", "--quiet", "-m", "start the atelier")
        atelier.run_git("remote", "add", "origin", FORGE_URL)
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(atelier.path))
        return remote

    def record_study(self, output: str, *project: str) -> None:
        self.run_study(
            "new",
            "trees",
            "--title",
            "the trees",
            *project,
            "--collector",
            "shell: printf 'oak\\n'",
            "--slot",
            "none",
            "--every",
            "1h",
            "--output",
            output,
        )

    def replace_pushed_commit(self, remote: TemporaryProject, branch: str) -> None:
        commit_of_an_earlier_second = remote.run_git(
            "commit-tree", f"{branch}^{{tree}}", "-p", f"{branch}^", "-m", "the answer of an earlier second"
        ).strip()
        remote.run_git("update-ref", f"refs/heads/{branch}", commit_of_an_earlier_second)

    def run_output(self) -> dict:
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "study", "run", "trees", "--json", environment=self.environment
        )
        return json.loads(completed.stdout)


class BrigadeStudyFileOutputTest(StudyOutputTestCase):
    def test_should_commit_the_markdown_of_the_answer_on_a_branch_of_the_project(self):
        # Arrange
        self.record_study("file:studies/{run}.md", "--project", "shop")

        # Act
        run_id = self.run_output()["run"]

        # Assert
        self.assertEqual(
            self.project.run_git("show", f"brigade/study-trees-{run_id}:studies/{run_id}.md"),
            f"# ANSWER trees_{run_id.replace('-', '_')}\n\n- STUDY: trees\n- RUN: {run_id}\n- COLLECTED: shell\n",
        )

    def test_should_leave_the_checkout_of_the_project_on_its_branch(self):
        # Arrange
        self.record_study("file:studies/{run}.md", "--project", "shop")

        # Act
        self.run_output()

        # Assert
        self.assertEqual(self.project.run_git("status", "--short", "--branch"), "## main\n")

    def test_should_push_the_branch_where_the_project_has_a_forge(self):
        # Arrange
        remote = self.add_forge_project()
        self.record_study("file:studies/{run}.md", "--project", "atelier")

        # Act
        run_id = self.run_output()["run"]

        # Assert
        self.assertEqual(
            remote.run_git("branch", "--list", f"brigade/study-trees-{run_id}"), f"  brigade/study-trees-{run_id}\n"
        )

    def test_should_open_a_pull_request_holding_the_markdown_where_the_project_has_a_forge(self):
        # Arrange
        self.add_forge_project()
        self.record_study("file:studies/{run}.md", "--project", "atelier")

        # Act
        run_id = self.run_output()["run"]

        # Assert
        self.assertEqual(
            self.gh_calls.read_text(),
            f"pr create --base main --head brigade/study-trees-{run_id} --title Study trees, run {run_id}"
            " --body-file -\n"
            f"# ANSWER trees_{run_id.replace('-', '_')}\n\n- STUDY: trees\n- RUN: {run_id}\n- COLLECTED: shell\n",
        )

    def test_should_resume_a_study_parked_once_its_branch_was_pushed(self):
        # Arrange
        flag = Path(self.root.name) / "forge-reachable"
        install_executable(self.tools / "gh", REFUSING_GH.format(flag=flag))
        remote = self.add_forge_project()
        self.record_study("file:studies/{run}.md", "--project", "atelier")
        parked_run = self.run_output()["run"]
        self.replace_pushed_commit(remote, f"brigade/study-trees-{parked_run}")
        flag.write_text("")

        # Act
        resumed = self.run_output()

        # Assert
        self.assertEqual(resumed["state"], "done")

    def test_should_park_a_study_with_no_project(self):
        # Arrange
        self.record_study("file:studies/{run}.md")

        # Act
        parked = self.run_output()

        # Assert
        self.assertEqual(parked["reason"], "the output file:studies/{run}.md needs a project")


class BrigadeStudyIssueOutputTest(StudyOutputTestCase):
    def test_should_open_an_issue_holding_the_markdown_of_the_answer(self):
        # Arrange
        self.add_forge_project()
        self.record_study("issue", "--project", "atelier")

        # Act
        run_id = self.run_output()["run"]

        # Assert
        self.assertEqual(
            self.gh_calls.read_text(),
            f"issue create --title Study trees, run {run_id} --body-file -\n"
            f"# ANSWER trees_{run_id.replace('-', '_')}\n\n- STUDY: trees\n- RUN: {run_id}\n- COLLECTED: shell\n",
        )

    def test_should_park_a_study_whose_project_has_no_forge(self):
        # Arrange
        self.record_study("issue", "--project", "shop")

        # Act
        parked = self.run_output()

        # Assert
        self.assertEqual(parked["reason"], "the output issue needs a project with a forge")


class BrigadeStudyOutputOnPathTest(StudyOutputTestCase):
    def test_should_hand_the_answer_to_the_output_on_path(self):
        # Arrange
        install_executable(self.tools / "brigade-output-notes", RECEIVING_OUTPUT.format(received=self.received))
        self.record_study("notes", "--project", "shop")

        # Act
        run_id = self.run_output()["run"]

        # Assert
        self.assertEqual(
            json.loads(self.received.read_text()),
            {
                "schema_version": 1,
                "study": "trees",
                "run": run_id,
                "markdown": f"# ANSWER trees_{run_id.replace('-', '_')}\n\n- STUDY: trees\n- RUN: {run_id}\n"
                "- COLLECTED: shell\n",
            },
        )

    def test_should_park_a_study_whose_output_is_found_nowhere(self):
        # Arrange
        self.record_study("notes", "--project", "shop")

        # Act
        parked = self.run_output()

        # Assert
        self.assertEqual(parked["reason"], "no output notes: no brigade-output-notes on PATH")


class BrigadeStudyCollectorTest(StudyRunTestCase):
    def record_digest(self, collector: str = "study name=trees") -> None:
        self.run_study(
            "new",
            "digest",
            "--title",
            "the digest",
            "--project",
            "shop",
            "--collector",
            collector,
            "--slot",
            "none",
            "--every",
            "daily@09:00",
            "--output",
            "entity:ANSWER",
        )

    def test_should_collect_the_last_answer_of_the_study_it_names(self):
        # Arrange
        self.record_scan("shell: printf 'oak\\n'")
        self.run_study("run", "trees")
        trees_run = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]
        self.record_digest()

        # Act
        digest_run = json.loads(self.run_study("run", "digest", "--json").stdout)["run"]

        # Assert
        document = self.runs / digest_run / "collectors" / "1" / "collect" / "study" / "document.json"
        self.assertEqual(
            json.loads(document.read_text())["items"],
            [
                {
                    "type": "ANSWER",
                    "name": f"trees_{trees_run.replace('-', '_')}",
                    "fields": [
                        {"name": "STUDY", "value": "trees"},
                        {"name": "RUN", "value": trees_run},
                        {"name": "COLLECTED", "value": "shell"},
                    ],
                }
            ],
        )

    def test_should_park_on_a_study_that_has_no_answer_yet(self):
        # Arrange
        self.record_scan("shell: printf 'oak\\n'")
        self.record_digest()

        # Act
        parked = json.loads(self.run_study("run", "digest", "--json").stdout)

        # Assert
        self.assertEqual(parked["reason"], "collector study exited 1\n@STUDY.trees has no answer yet")

    def test_should_park_on_a_study_collector_naming_no_study(self):
        # Arrange
        self.record_digest("study")

        # Act
        parked = json.loads(self.run_study("run", "digest", "--json").stdout)

        # Assert
        self.assertEqual(parked["reason"], "collector study exited 1\nthe study collector takes name=<study>")


class BrigadeStudyListTest(StudyRunTestCase):
    def record_weekly(self) -> None:
        self.run_study(
            "new",
            "weekly",
            "--title",
            "what moved this week",
            "--question",
            QUESTION,
            "--collector",
            "shell: true",
            "--every",
            "mon@09:00",
            "--output",
            "entity:ANSWER",
        )

    def test_should_list_every_study_with_its_schedule_its_last_run_and_its_outcome(self):
        # Arrange
        self.record_scan("shell: true")
        trees_run = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]
        self.record_weekly()

        # Act
        completed = self.run_study("list", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "studies": [
                    {"name": "trees", "status": "active", "every": "1h", "last_run": trees_run, "outcome": "done"},
                    {"name": "weekly", "status": "active", "every": "mon@09:00", "last_run": None, "outcome": None},
                ],
            },
        )

    def test_should_print_the_studies_as_a_table(self):
        # Arrange
        self.record_weekly()

        # Act
        completed = self.run_study("list")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(
            completed.stdout, "name    status  every      last run  outcome\nweekly  active  mon@09:00  -         -\n"
        )

    def test_should_print_that_no_study_is_recorded(self):
        # Act
        completed = self.run_study("list")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "no study recorded\n")


class BrigadeStudyShowTest(StudyRunTestCase):
    def test_should_present_the_fields_of_the_study_and_its_last_run(self):
        # Arrange
        self.record_scan("shell: true")
        trees_run = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]

        # Act
        completed = self.run_study("show", "trees", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "study": {
                    "name": "trees",
                    "fields": [
                        {"name": "TITLE", "value": "the trees"},
                        {"name": "PROJECT", "value": "@PROJECT.shop"},
                        {"name": "COLLECTOR", "value": "shell: true"},
                        {"name": "SLOT", "value": "none"},
                        {"name": "EVERY", "value": "1h"},
                        {"name": "OUTPUT", "value": "entity:ANSWER"},
                        {"name": "ANSWER", "value": "ANSWER"},
                        {"name": "STATUS", "value": "active"},
                    ],
                    "last_run": trees_run,
                    "outcome": "done",
                },
            },
        )

    def test_should_print_the_fields_of_a_study_that_never_ran(self):
        # Arrange
        self.record_scan("shell: true")

        # Act
        completed = self.run_study("show", "trees")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(
            completed.stdout,
            "@STUDY.trees\n"
            "TITLE       the trees\n"
            "PROJECT     @PROJECT.shop\n"
            "COLLECTOR   shell: true\n"
            "SLOT        none\n"
            "EVERY       1h\n"
            "OUTPUT      entity:ANSWER\n"
            "ANSWER      ANSWER\n"
            "STATUS      active\n"
            "last run    -\n"
            "outcome     -\n",
        )

    def test_should_exit_1_naming_a_study_that_is_not_defined(self):
        # Act
        completed = self.run_study("show", "ghost")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade study show: @STUDY.ghost is not defined in the operational corpus\n"
        )


class BrigadeStudyPauseAndResumeTest(StudyRunTestCase):
    def setUp(self):
        super().setUp()
        self.record_scan("shell: true")

    def count_commits(self) -> str:
        return self.machine.read_git("rev-list", "--count", "HEAD")

    def test_should_pause_the_study_and_commit_the_studies(self):
        # Act
        completed = self.run_study("pause", "trees", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout), {"schema_version": 1, "study": "trees", "status": "paused", "changed": True}
        )
        self.assertEqual(self.read_studies().splitlines()[-1], "\tSTATUS paused")
        self.assertEqual(
            self.machine.read_git("log", "-1", "--format=%s", "--name-only"),
            "brigade study pause: trees\n\nstudies.awawa\n",
        )

    def test_should_resume_a_paused_study(self):
        # Arrange
        self.run_study("pause", "trees")

        # Act
        completed = self.run_study("resume", "trees")

        # Assert
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "resumed @STUDY.trees\n")
        self.assertEqual(self.read_studies().splitlines()[-1], "\tSTATUS active")

    def test_should_leave_a_study_already_in_that_status_as_it_is(self):
        # Arrange
        rows = [
            ("pause", "paused", "@STUDY.trees is already paused\n"),
            ("resume", "active", "@STUDY.trees is already active\n"),
        ]
        for action, status, text in rows:
            with self.subTest(action=action):
                # Arrange
                self.run_study(action, "trees")
                commits = self.count_commits()

                # Act
                completed = self.run_study(action, "trees")

                # Assert
                self.assertEqual(completed.returncode, 0)
                self.assertEqual(completed.stdout, text)
                self.assertEqual(self.read_studies().splitlines()[-1], f"\tSTATUS {status}")
                self.assertEqual(self.count_commits(), commits)

    def test_should_exit_1_naming_a_study_that_is_not_defined(self):
        for action in ["pause", "resume"]:
            with self.subTest(action=action):
                # Act
                completed = self.run_study(action, "ghost")

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(
                    completed.stderr, f"brigade study {action}: @STUDY.ghost is not defined in the operational corpus\n"
                )

    def test_should_exit_1_naming_an_archived_study_it_leaves_archived(self):
        # Arrange
        studies = self.machine.corpus / "studies.awawa"
        studies.write_text(self.read_studies().replace("\tSTATUS active", "\tSTATUS archived"))
        self.machine.read_git("commit", "--quiet", "--all", "-m", "archive the trees")
        for action in ["pause", "resume"]:
            with self.subTest(action=action):
                # Act
                completed = self.run_study(action, "trees")

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(
                    completed.stderr,
                    f"brigade study {action}: @STUDY.trees is archived; it is neither paused nor resumed\n",
                )
                self.assertEqual(self.read_studies().splitlines()[-1], "\tSTATUS archived")

    def test_should_exit_1_naming_a_study_written_outside_the_studies_file(self):
        # Arrange
        (self.machine.corpus / "hand.awawa").write_text(self.read_studies())
        (self.machine.corpus / "studies.awawa").write_text("")
        self.machine.read_git("add", "hand.awawa")
        self.machine.read_git("commit", "--quiet", "--all", "-m", "move the trees by hand")

        # Act
        completed = self.run_study("pause", "trees")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade study pause: @STUDY.trees is not written in studies.awawa\n")
