import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError, CorpusLintFailed
from brigade.ledger.append_event import append_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.plan_lint_failed import PlanLintFailed
from brigade.ledger.read_ledger import read_ledger
from brigade.planning.read_planning_request import PlanningRequest
from brigade.planning.record_plan import PlanRecording, record_plan
from tests.unit.create_scripted_runtime import RUNTIME_NOW, create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

PLAN = 'MILESTONE F1\n\tTITLE "Printer"\n\nTASK B20\n\tTITLE "the printer"\n\tMILESTONE @MILESTONE.F1\n'
BRANCH = "plan/oak_r1"
PUSH = ("git", "push", "--quiet", "origin", BRANCH)
PLANNED_FILES = ("corpus/milestones.awawa", "corpus/tasks.awawa")
BRANCH_FOUND = 0
BRANCH_NOT_FOUND = 1
NO_PULL_REQUEST = {"schema_version": 1, "pull_request": None}
NO_REVIEW_REQUIRED = None
NO_POLICY = {}
ASKING_POLICY = {"oak_plans": (("PROJECT", "@PROJECT.oak"), ("PLAN_REVIEW", "ask"))}
MAIN_HELD_BY_NO_WORKTREE = "worktree /srv/oak\0HEAD c0ffee\0branch refs/heads/feature\0\0"
MAIN_HELD_BY_THE_CHECKOUT = "worktree /srv/oak\0HEAD c0ffee\0branch refs/heads/main\0\0"
MAIN_HOLDS_THE_PLAN = 0
MAIN_LACKS_THE_PLAN = 1


def create_found_pull_request(review: str | None, state: str = "open") -> dict:
    return {
        "schema_version": 1,
        "pull_request": {
            "number": 42,
            "state": state,
            "checks": [],
            "review": review,
            "behind": False,
            "head": "c0ffee",
            "base": "main",
        },
    }


def read_environment(key: str) -> dict:
    return {"GH_TOKEN": f"token-of-{key}"}


class ForgeDouble:
    def __init__(self, found_pull_requests: list[dict]):
        self.found_pull_requests = found_pull_requests
        self.calls = []

    def find_pull_request(self, request: dict, runtime) -> dict:
        self.calls.append(("find_pull_request", request))
        return self.found_pull_requests.pop(0)

    def open_pull_request(self, request: dict, runtime) -> dict:
        self.calls.append(("open_pull_request", request))
        return {"number": 42}

    def approve_pull_request(self, request: dict, runtime) -> None:
        self.calls.append(("approve_pull_request", request))

    def merge_pull_request(self, request: dict, runtime) -> None:
        self.calls.append(("merge_pull_request", request))

    def list_operations(self) -> list[str]:
        return [operation for operation, request in self.calls]


class RecordPlanArrangement:
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.plan_file = self.root / "plan.awawa"
        self.plan_file.write_text(PLAN, encoding="utf-8")
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes, run_directory=self.root / "runs" / "r1")
        self.worktree = self.root / "cache" / "plans" / "oak_r1"
        (self.worktree / "corpus").mkdir(parents=True)
        (self.worktree / "corpus" / "tasks.awawa").write_text('TASK B19\n\tTITLE "the parser"\n', encoding="utf-8")
        self.config_root = self.runtime.paths.config_root
        (self.config_root / "requests.awawa").write_text("REQUEST oak_r1\n\tSTATUS planning\n", encoding="utf-8")
        self.processes.answer(("git", "worktree", "add", "--quiet", "--detach", str(self.worktree), "main"))
        self.processes.answer(("git", "worktree", "remove", "--force", str(self.worktree)))
        self.forge = ForgeDouble([create_found_pull_request(NO_REVIEW_REQUIRED)])

    def script_plan_entities(self, entities: list[dict]) -> None:
        plan_file = str(self.plan_file)
        self.processes.answer_json(("awawa", "show", plan_file, "--json", plan_file), {"entities": entities})

    def script_plan_entity(self, target: str, fields: list[dict]) -> None:
        plan_file = str(self.plan_file)
        self.processes.answer_json(("awawa", "show", target, "--json", plan_file), {"fields": fields})

    def script_corpus_sites(self, sites: list[dict]) -> None:
        self.processes.answer_json(("awawa", "status", "--json", str(self.worktree)), {"entities": sites})

    def script_skeletons(self) -> None:
        self.processes.answer(
            ("awawa", "new", "MILESTONE", "F1", str(self.worktree)), stdout='MILESTONE F1\n\tTITLE ""\n'
        )
        self.processes.answer(
            ("awawa", "new", "TASK", "B20", str(self.worktree)),
            stdout='TASK B20\n\tTITLE ""\n\tMILESTONE @MILESTONE.X\n',
        )

    def script_valid_plan(self) -> None:
        self.script_plan_entities([{"type": "MILESTONE", "name": "F1"}, {"type": "TASK", "name": "B20"}])
        self.script_plan_entity("@MILESTONE.F1", [{"name": "TITLE", "atoms": ['"Printer"']}])
        self.script_plan_entity(
            "@TASK.B20",
            [{"name": "TITLE", "atoms": ['"the printer"']}, {"name": "MILESTONE", "atoms": ["@MILESTONE.F1"]}],
        )
        self.script_corpus_sites([{"type": "TASK", "name": "B19", "file": "corpus/tasks.awawa", "line": 1}])
        self.script_skeletons()
        self.script_plan_branch(BRANCH_NOT_FOUND)

    def script_plan_branch(self, exit_code: int) -> None:
        self.processes.answer(("git", "rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}"), exit_code=exit_code)

    def script_marking(self) -> None:
        self.processes.answer_json(
            ("awawa", "status", "--json", str(self.config_root)),
            {"entities": [{"type": "REQUEST", "name": "oak_r1", "file": "requests.awawa", "line": 1}]},
        )
        self.processes.answer_corpus_change(
            self.config_root, ("requests.awawa",), "brigade plan record: @REQUEST.oak_r1 planned"
        )

    def script_policies(self, policies: dict) -> None:
        self.processes.answer_entities(self.config_root, "POLICY", policies)

    def script_recording(self) -> None:
        self.script_valid_plan()
        self.processes.answer_corpus_change(self.worktree, PLANNED_FILES, f"brigade plan record: {BRANCH}")
        self.processes.answer(("git", "switch", "--quiet", "--create", BRANCH))
        self.processes.answer(PUSH)
        self.script_policies(NO_POLICY)
        self.script_marking()

    def script_refused_lint(self) -> None:
        self.script_valid_plan()
        self.processes.answer_corpus_change(self.worktree, PLANNED_FILES, "unused", lint_output="L012 dangling")
        self.processes.answer(
            ("git", "ls-tree", "--name-only", "HEAD", "--", *PLANNED_FILES), stdout="corpus/tasks.awawa\n"
        )
        self.processes.answer(("git", "checkout", "HEAD", "--", "corpus/tasks.awawa"))
        self.processes.answer(("git", "rm", "--cached", "--quiet", "--ignore-unmatch", "--", "corpus/milestones.awawa"))
        self.processes.answer(("git", "clean", "--force", "--quiet", "--", "corpus/milestones.awawa"))

    def create_recording(self, forge: str = "github") -> PlanRecording:
        project = Entity(
            name="oak",
            fields=(
                EntityField(name="PATH", value="/srv/oak"),
                EntityField(name="MAIN", value="main"),
                EntityField(name="CORPUS", value="corpus"),
                EntityField(name="FORGE", value=forge),
            ),
        )
        return PlanRecording(
            request=PlanningRequest(name="oak_r1", project="oak", text="print"),
            project=project,
            plan_file=self.plan_file,
            forge=self.forge,
            read_environment=read_environment,
        )


class RecordPlanTest(RecordPlanArrangement, unittest.TestCase):
    def test_should_record_the_plan_on_its_plan_branch_and_its_pull_request(self):
        # Arrange
        self.script_recording()

        # Act
        recorded = record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(recorded, {"request": "oak_r1", "milestone": "F1", "branch": BRANCH, "pr": 42})

    def test_should_write_the_planned_milestone_in_a_new_file_of_its_type(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            (self.worktree / "corpus" / "milestones.awawa").read_text(encoding="utf-8"),
            'MILESTONE F1\n\tTITLE "Printer"\n',
        )

    def test_should_append_the_planned_task_to_the_file_holding_the_tasks(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            (self.worktree / "corpus" / "tasks.awawa").read_text(encoding="utf-8"),
            'TASK B19\n\tTITLE "the parser"\n\nTASK B20\n\tTITLE "the printer"\n\tMILESTONE @MILESTONE.F1\n',
        )

    def test_should_mark_the_request_planned_on_its_milestone_and_its_pull_request(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            (self.config_root / "requests.awawa").read_text(encoding="utf-8"),
            'REQUEST oak_r1\n\tSTATUS planned\n\tMILESTONE "F1"\n\tPR 42\n',
        )

    def test_should_push_the_plan_branch_and_open_its_pull_request_to_the_main_branch(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertIn(PUSH, self.processes.list_argvs())
        self.assertEqual(
            self.forge.calls[0],
            (
                "open_pull_request",
                {
                    "repository": "/srv/oak",
                    "base": "main",
                    "branch": BRANCH,
                    "title": "docs(plan): Printer (@REQUEST.oak_r1)",
                    "body": "print",
                    "milestone": None,
                    "environment": {"GH_TOKEN": "token-of-cli"},
                },
            ),
        )

    def test_should_merge_the_plan_pull_request_itself_under_the_automatic_review(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            self.forge.calls[-1],
            (
                "merge_pull_request",
                {
                    "repository": "/srv/oak",
                    "number": 42,
                    "method": "squash",
                    "environment": {"GH_TOKEN": "token-of-cli"},
                },
            ),
        )

    def test_should_leave_the_plan_pull_request_to_the_user_under_the_asking_review(self):
        # Arrange
        self.script_recording()
        self.script_policies(ASKING_POLICY)

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(self.forge.list_operations(), ["open_pull_request"])

    def test_should_approve_with_the_review_login_before_merging_where_the_forge_requires_a_review(self):
        # Arrange
        self.script_recording()
        self.forge.found_pull_requests = [create_found_pull_request("review_required")]

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            self.forge.calls[2:],
            [
                (
                    "approve_pull_request",
                    {"repository": "/srv/oak", "number": 42, "environment": {"GH_TOKEN": "token-of-review"}},
                ),
                (
                    "merge_pull_request",
                    {
                        "repository": "/srv/oak",
                        "number": 42,
                        "method": "squash",
                        "environment": {"GH_TOKEN": "token-of-cli"},
                    },
                ),
            ],
        )

    def test_should_remove_the_worktree_the_plan_was_checked_in(self):
        # Arrange
        self.script_recording()

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertIn(("git", "worktree", "remove", "--force", str(self.worktree)), self.processes.list_argvs())


class RecordPlanWithoutForgeTest(RecordPlanArrangement, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.script_recording()

    def test_should_merge_the_plan_branch_into_the_main_branch_no_worktree_holds(self):
        # Arrange
        self.processes.answer(("git", "worktree", "list", "--porcelain", "-z"), stdout=MAIN_HELD_BY_NO_WORKTREE)
        self.processes.answer(("git", "fetch", "--quiet", ".", f"{BRANCH}:main"))

        # Act
        recorded = record_plan(self.runtime, self.create_recording("none"))

        # Assert
        self.assertEqual(recorded, {"request": "oak_r1", "milestone": "F1", "branch": BRANCH, "pr": None})
        self.assertIn(("git", "fetch", "--quiet", ".", f"{BRANCH}:main"), self.processes.list_argvs())

    def test_should_merge_the_plan_branch_in_the_worktree_holding_the_main_branch(self):
        # Arrange
        self.processes.answer(("git", "worktree", "list", "--porcelain", "-z"), stdout=MAIN_HELD_BY_THE_CHECKOUT)
        self.processes.answer(("git", "merge", "--quiet", "--ff-only", BRANCH))

        # Act
        record_plan(self.runtime, self.create_recording("none"))

        # Assert
        merge = next(request for request in self.processes.requests if request.argv[:2] == ("git", "merge"))
        self.assertEqual(merge.cwd, "/srv/oak")

    def test_should_mark_the_request_planned_with_no_pull_request_and_push_nothing(self):
        # Arrange
        self.processes.answer(("git", "worktree", "list", "--porcelain", "-z"), stdout=MAIN_HELD_BY_NO_WORKTREE)
        self.processes.answer(("git", "fetch", "--quiet", ".", f"{BRANCH}:main"))

        # Act
        record_plan(self.runtime, self.create_recording("none"))

        # Assert
        self.assertEqual(
            (self.config_root / "requests.awawa").read_text(encoding="utf-8"),
            'REQUEST oak_r1\n\tSTATUS planned\n\tMILESTONE "F1"\n',
        )
        self.assertNotIn(PUSH, self.processes.list_argvs())


class RecordPlanReplayTest(RecordPlanArrangement, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.script_plan_entities([{"type": "MILESTONE", "name": "F1"}, {"type": "TASK", "name": "B20"}])
        self.script_plan_entity("@MILESTONE.F1", [{"name": "TITLE", "atoms": ['"Printer"']}])
        self.script_plan_entity(
            "@TASK.B20",
            [{"name": "TITLE", "atoms": ['"the printer"']}, {"name": "MILESTONE", "atoms": ["@MILESTONE.F1"]}],
        )
        self.script_plan_branch(BRANCH_FOUND)
        self.script_marking()

    def script_main_ancestry(self, exit_code: int) -> None:
        self.processes.answer(("git", "merge-base", "--is-ancestor", BRANCH, "main"), exit_code=exit_code)

    def test_should_reuse_the_merged_pull_request_of_the_plan_branch_and_mark_the_request_planned_alone(self):
        # Arrange
        self.forge.found_pull_requests = [create_found_pull_request(NO_REVIEW_REQUIRED, "merged")]

        # Act
        recorded = record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(recorded, {"request": "oak_r1", "milestone": "F1", "branch": BRANCH, "pr": 42})
        self.assertEqual(self.forge.list_operations(), ["find_pull_request"])
        self.assertEqual(
            (self.config_root / "requests.awawa").read_text(encoding="utf-8"),
            'REQUEST oak_r1\n\tSTATUS planned\n\tMILESTONE "F1"\n\tPR 42\n',
        )

    def test_should_merge_the_open_pull_request_of_the_plan_branch_under_the_automatic_review(self):
        # Arrange
        self.forge.found_pull_requests = [
            create_found_pull_request(NO_REVIEW_REQUIRED),
            create_found_pull_request(NO_REVIEW_REQUIRED),
        ]
        self.script_policies(NO_POLICY)

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            self.forge.calls[-1],
            (
                "merge_pull_request",
                {
                    "repository": "/srv/oak",
                    "number": 42,
                    "method": "squash",
                    "environment": {"GH_TOKEN": "token-of-cli"},
                },
            ),
        )

    def test_should_leave_the_open_pull_request_of_the_plan_branch_to_the_user_under_the_asking_review(self):
        # Arrange
        self.script_policies(ASKING_POLICY)

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(self.forge.list_operations(), ["find_pull_request"])

    def test_should_open_the_pull_request_the_plan_branch_lacks(self):
        # Arrange
        self.forge.found_pull_requests = [NO_PULL_REQUEST, create_found_pull_request(NO_REVIEW_REQUIRED)]
        self.processes.answer(PUSH)
        self.script_policies(NO_POLICY)

        # Act
        record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            self.forge.list_operations(),
            ["find_pull_request", "open_pull_request", "find_pull_request", "merge_pull_request"],
        )

    def test_should_mark_the_request_planned_alone_when_the_main_branch_holds_the_plan_without_a_forge(self):
        # Arrange
        self.script_main_ancestry(MAIN_HOLDS_THE_PLAN)

        # Act
        recorded = record_plan(self.runtime, self.create_recording("none"))

        # Assert
        self.assertEqual(recorded, {"request": "oak_r1", "milestone": "F1", "branch": BRANCH, "pr": None})
        self.assertEqual(self.forge.list_operations(), [])

    def test_should_merge_the_plan_branch_the_main_branch_lacks_without_a_forge(self):
        # Arrange
        self.script_main_ancestry(MAIN_LACKS_THE_PLAN)
        self.processes.answer(("git", "worktree", "list", "--porcelain", "-z"), stdout=MAIN_HELD_BY_NO_WORKTREE)
        self.processes.answer(("git", "fetch", "--quiet", ".", f"{BRANCH}:main"))

        # Act
        record_plan(self.runtime, self.create_recording("none"))

        # Assert
        self.assertIn(("git", "fetch", "--quiet", ".", f"{BRANCH}:main"), self.processes.list_argvs())


class RecordPlanLintTest(RecordPlanArrangement, unittest.TestCase):
    def test_should_record_the_lint_round_the_plan_spent(self):
        # Arrange
        self.script_refused_lint()

        # Act
        with self.assertRaises(CorpusLintFailed):
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (LedgerEntry(instant=RUNTIME_NOW, event=PlanLintFailed(request="oak_r1", run="r1")),),
        )

    def test_should_record_the_lint_round_of_a_recording_outside_a_run_with_no_run(self):
        # Arrange
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.script_refused_lint()

        # Act
        with self.assertRaises(CorpusLintFailed):
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (LedgerEntry(instant=RUNTIME_NOW, event=PlanLintFailed(request="oak_r1", run=None)),),
        )

    def test_should_refuse_a_second_lint_round_in_the_same_run(self):
        # Arrange
        append_event(
            self.runtime.paths, datetime(2026, 10, 19, 8, 0, tzinfo=UTC), PlanLintFailed(request="oak_r1", run="r1")
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(str(refusal.exception), "@REQUEST.oak_r1 spent its lint round in run r1; the run ends blocked")


class RecordPlanRefusalTest(RecordPlanArrangement, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.script_plan_branch(BRANCH_NOT_FOUND)

    def test_should_refuse_a_planned_entity_the_corpus_already_holds(self):
        # Arrange
        self.script_plan_entities([{"type": "TASK", "name": "B19"}])
        self.script_plan_entity("@TASK.B19", [{"name": "TITLE", "atoms": ['"again"']}])
        self.script_corpus_sites([{"type": "TASK", "name": "B19", "file": "corpus/tasks.awawa", "line": 1}])

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(str(refusal.exception), "@TASK.B19 already exists at corpus/tasks.awawa:1")

    def test_should_refuse_a_planned_field_the_schema_does_not_declare(self):
        # Arrange
        self.script_plan_entities([{"type": "MILESTONE", "name": "F1"}])
        self.script_plan_entity(
            "@MILESTONE.F1", [{"name": "TITLE", "atoms": ['"Printer"']}, {"name": "OWNER", "atoms": ['"ada"']}]
        )
        self.script_corpus_sites([])
        self.script_skeletons()

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the schema of the corpus of @PROJECT.oak does not declare the field OWNER of MILESTONE",
        )

    def test_should_refuse_a_plan_holding_neither_a_milestone_nor_a_task(self):
        # Arrange
        self.script_plan_entities([{"type": "DECISION", "name": "D9"}])
        self.script_plan_entity("@DECISION.D9", [])
        self.script_corpus_sites([])
        self.processes.answer(("awawa", "new", "DECISION", "D9", str(self.worktree)), stdout="DECISION D9\n")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(str(refusal.exception), "the plan holds @DECISION.D9, which is neither a MILESTONE nor a TASK")

    def test_should_refuse_a_plan_without_exactly_one_milestone(self):
        # Arrange
        self.script_plan_entities([{"type": "TASK", "name": "B20"}])
        self.script_plan_entity("@TASK.B20", [{"name": "TITLE", "atoms": ['"the printer"']}])
        self.script_corpus_sites([])
        self.script_skeletons()

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(str(refusal.exception), "the plan holds 0 MILESTONE entities, not one")

    def test_should_refuse_a_task_planned_on_another_milestone(self):
        # Arrange
        self.script_plan_entities([{"type": "MILESTONE", "name": "F1"}, {"type": "TASK", "name": "B20"}])
        self.script_plan_entity("@MILESTONE.F1", [{"name": "TITLE", "atoms": ['"Printer"']}])
        self.script_plan_entity(
            "@TASK.B20",
            [{"name": "TITLE", "atoms": ['"the printer"']}, {"name": "MILESTONE", "atoms": ["@MILESTONE.F0"]}],
        )
        self.script_corpus_sites([])
        self.script_skeletons()

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            record_plan(self.runtime, self.create_recording())

        # Assert
        self.assertEqual(str(refusal.exception), "the plan holds @TASK.B20, whose MILESTONE is not @MILESTONE.F1")
