import json
import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

PINNED_COMMIT_DATES = {"GIT_AUTHOR_DATE": "2026-10-12T09:00:00Z", "GIT_COMMITTER_DATE": "2026-10-12T09:00:00Z"}
QUESTION = "what changed in the shop this week?"


class StudyTestCase(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
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
            "1d",
            "--output",
            "inbox",
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
            '\tEVERY "1d"\n'
            '\tOUTPUT "inbox"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )

    def test_should_commit_the_study(self):
        # Act
        self.run_study(
            "new", "weekly", "--title", "what moved", "--collector", "worktrees", "--every", "1d", "--output", "inbox"
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
            "inbox",
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
            '\tOUTPUT "inbox"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )

    def test_should_print_the_study_recorded(self):
        # Act
        completed = self.run_study(
            "new", "weekly", "--title", "what moved", "--collector", "worktrees", "--every", "1d", "--output", "inbox"
        )

        # Assert
        self.assertEqual(completed.stdout, "@STUDY.weekly recorded, every 1d\n")

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
            "1d",
            "--output",
            "inbox",
            "--answer",
            "VERDICT",
        )

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade study new: the schema of the operational corpus declares no VERDICT\n"),
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
            "1d",
            "--output",
            "inbox",
        )

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr), (1, "brigade study new: @PROJECT.cart is not registered\n")
        )


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
        self.assertEqual(sorted(path.name for path in steps.iterdir()), ["collect.json", "judge.json", "output.json"])

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
            "1d",
            "--output",
            "entity:ANSWER",
        )

        # Act
        completed = self.run_study("run", "weekly", "--json")

        # Assert
        document = json.loads(completed.stdout)
        [judging] = self.read_events("run.finished")
        self.assertEqual(
            (document["state"], document["reason"], judging["procedure"]),
            ("parked", f"the judging run {judging['run']} gave no answer", "study"),
        )

    def test_should_exit_1_naming_a_study_that_is_not_defined(self):
        # Act
        completed = self.run_study("run", "absent")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade study run: @STUDY.absent is not defined in the operational corpus\n"),
        )


class BrigadeRunsPruneOfStudyRunsTest(StudyRunTestCase):
    def test_should_remove_a_done_study_run_settled_before_the_day(self):
        # Arrange
        self.record_scan("shell: true")
        done = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]

        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "runs", "prune", "--before", "2099-01-01")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout), (0, f"removed {done} (finished)\n"), completed.stderr
        )

    def test_should_spare_a_parked_study_run_the_next_study_run_resumes(self):
        # Arrange
        self.record_scan("shell: cat flag")
        parked = json.loads(self.run_study("run", "trees", "--json").stdout)["run"]

        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "runs", "prune", "--before", "2099-01-01")

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (0, "no run removed\n"), completed.stderr)
        self.assertEqual([path.name for path in self.runs.iterdir()], [parked])


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
        self.assertEqual(
            (package["question"], package["collected"]),
            (QUESTION, [{"collector": "shell", "summary": {"lines": 2}, "document": str(self.document)}]),
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
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade study context: 20261015T000000Z-000000 is not a run of a study\n"),
        )

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
        [parked] = [path.name for path in self.runs.iterdir() if path.name != self.run_id]

        # Act
        completed = self.run_study("context", parked)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, f"brigade study context: the run {parked} has collected no evidence yet\n"),
        )


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
            "1d",
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
        self.assertEqual(
            (completed.returncode, (self.runs / self.run_id / "answer.awawa").read_text()),
            (0, self.answer_file.read_text()),
            completed.stderr,
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
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade study answer: the answer changed COLLECTED, a field brigade filled\n"),
        )

    def test_should_keep_no_answer_it_refused(self):
        # Arrange
        self.write_answer('"{\\"lines\\": 3}"', '\tNARRATIVE "three lines moved"\n')

        # Act
        self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(sorted(path.name for path in (self.runs / self.run_id).glob("*.awawa")), [])

    def test_should_refuse_an_answer_that_names_another_entity(self):
        # Arrange
        self.answer_file.write_text('ANSWER elsewhere\n\tSTUDY "weekly"\n\tRUN "elsewhere"\n')

        # Act
        completed = self.run_study("answer", self.run_id, "--file", str(self.answer_file))

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, f"brigade study answer: the answer holds no @ANSWER.weekly_{self.run_id.replace('-', '_')}\n"),
        )
