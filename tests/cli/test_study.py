import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.cli.test_collect import install_executable
from tests.list_entry_names import list_entry_names
from tests.value_matchers import PatternMatcher

SHA256_DIGEST = PatternMatcher("^[0-9a-f]{64}$")
NO_EDIT_TOOL_NAMED = {
    "steps_to_first_edit": "the client names no edit tool",
    "tokens_to_first_edit": "the client names no edit tool",
}

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

    def read_events(self) -> list:
        [month] = self.ledger.glob("*.jsonl")
        return list(map(json.loads, month.read_text().splitlines()))


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

    def test_should_print_the_step_a_study_parked_at(self):
        # Arrange
        self.record_scan("shell: cat flag")

        # Act
        completed = self.run_study("run", "trees")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertRegex(completed.stdout, r"^@STUDY\.trees run \d{8}T\d{6}Z-[0-9a-f]{6} parked at collect: ")

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
        self.assertEqual(completed.returncode, 0, completed.stderr)
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
        events = self.read_events()
        [_, _, judging, _, _] = events
        study_run = document["run"]
        reason = f"the judging run {judging['run']} gave no answer"
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "study": "weekly",
                "run": study_run,
                "state": "parked",
                "step": "judge",
                "reason": reason,
            },
        )
        self.assertEqual(
            events,
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "order.started",
                    "project": "shop",
                    "kind": "study",
                    "order": "weekly",
                    "run": study_run,
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "step.done",
                    "kind": "study",
                    "run": study_run,
                    "step": "collect",
                },
                {
                    "schema_version": 2,
                    "ts": ANY,
                    "event": "run.finished",
                    "run": judging["run"],
                    "segment": 1,
                    "procedure": "study",
                    "slot": "report",
                    "role": "reporter",
                    "client": "fake",
                    "project": "shop",
                    "session": "fake-session",
                    "main_steps": 12,
                    "total_steps": None,
                    "duration_ms": ANY,
                    "usage": {
                        "input_tokens": 120,
                        "output_tokens": 3400,
                        "cache_creation_input_tokens": 16778,
                        "cache_read_input_tokens": 98000,
                    },
                    "outcome": "done",
                    "error_class": None,
                    "exit": 0,
                    "wave": None,
                    "task": None,
                    "role_digest": SHA256_DIGEST,
                    "procedure_digest": SHA256_DIGEST,
                    "shipped_budget": 40,
                    "nulls": {
                        **NO_EDIT_TOOL_NAMED,
                        "wave": "not launched by a wave",
                        "task": "not launched for a task",
                        "total_steps": "the client reads no transcript",
                        "error_class": "the run did not fail",
                    },
                    "cost_usd": 0.42,
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "step.failed",
                    "kind": "study",
                    "run": study_run,
                    "step": "judge",
                    "reason": reason,
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "order.parked",
                    "project": "shop",
                    "kind": "study",
                    "order": "weekly",
                    "run": study_run,
                    "step": "judge",
                    "reason": reason,
                },
            ],
        )

    def test_should_exit_1_naming_a_study_that_is_not_defined(self):
        # Act
        completed = self.run_study("run", "absent")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade study run: @STUDY.absent is not defined in the operational corpus\n"
        )


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

    def test_should_print_the_question_the_evidence_and_the_prose_fields(self):
        # Act
        completed = self.run_study("context", self.run_id)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
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


FAKE_GH = '#!/bin/sh\nprintf \'%s\\n\' "$*" >> "{calls}"\ncat >> "{calls}"\necho https://github.com/acme/atelier/7\n'
REFUSING_GH = '#!/bin/sh\n[ -f "{flag}" ] || exit 1\necho https://github.com/acme/atelier/7\n'
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
                    {"name": "triage", "status": "active", "every": "24h", "last_run": None, "outcome": None},
                    {"name": "corpus_lint_shop", "status": "active", "every": "24h", "last_run": None, "outcome": None},
                    {"name": "corpus_fmt_shop", "status": "active", "every": "24h", "last_run": None, "outcome": None},
                    {
                        "name": "stale_branches_shop",
                        "status": "active",
                        "every": "24h",
                        "last_run": None,
                        "outcome": None,
                    },
                    {"name": "worktrees_shop", "status": "active", "every": "24h", "last_run": None, "outcome": None},
                ],
            },
        )


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


class BrigadeStudyPauseAndResumeTest(StudyRunTestCase):
    def setUp(self):
        super().setUp()
        self.record_scan("shell: true")

    def test_should_pause_the_study_and_commit_the_studies(self):
        # Act
        completed = self.run_study("pause", "trees", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout), {"schema_version": 1, "study": "trees", "status": "paused", "changed": True}
        )
        self.assertEqual(
            self.read_studies(),
            "STUDY trees\n"
            '\tTITLE "the trees"\n'
            "\tPROJECT @PROJECT.shop\n"
            '\tCOLLECTOR "shell: true"\n'
            "\tSLOT none\n"
            '\tEVERY "1h"\n'
            '\tOUTPUT "entity:ANSWER"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS paused\n",
        )
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
        self.assertEqual(
            self.read_studies(),
            "STUDY trees\n"
            '\tTITLE "the trees"\n'
            "\tPROJECT @PROJECT.shop\n"
            '\tCOLLECTOR "shell: true"\n'
            "\tSLOT none\n"
            '\tEVERY "1h"\n'
            '\tOUTPUT "entity:ANSWER"\n'
            '\tANSWER "ANSWER"\n'
            "\tSTATUS active\n",
        )
