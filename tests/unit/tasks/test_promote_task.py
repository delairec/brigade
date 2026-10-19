import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.tasks.promote_task import TaskPromotionDemand, promote_task
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

TASKS = 'TASK B12\n\tTITLE "The parser"\n\tSTATUS todo\n\tDELIVERED_BY 40\n\nTASK B13\n\tSTATUS todo\n'
DECLARED_SCHEMA = {
    "fields": [
        {"name": "FIELD", "atoms": ["STATUS", "draft|todo|implemented"]},
        {"name": "FIELD", "atoms": ["DELIVERED_BY", "integer"]},
        {"name": "DESC", "atoms": ['"a task"']},
    ]
}
MESSAGE = "docs(corpus): mark @TASK.B12 implemented, delivered by #42\n\nCo-Authored-By: Ada <ada@example.org>"


class PromoteTaskTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.worktree = self.root / "oak-b12"
        (self.worktree / "corpus").mkdir(parents=True)
        (self.worktree / "corpus" / "tasks.awawa").write_text(TASKS, encoding="utf-8")
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        config_root = self.runtime.paths.config_root
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout=f"{self.worktree}\n")
        self.processes.answer(("git", "branch", "--show-current"), stdout="task/f0-parser/B12\n")
        self.processes.answer(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n"
        )
        self.processes.answer_entities(config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
        self.processes.answer_entities(
            config_root,
            "REQUEST",
            {"oak_1": (("PROJECT", "@PROJECT.oak"), ("BRANCH", "integration/f0-parser"))},
            ("PROJECT==@PROJECT.oak", "BRANCH==integration/f0-parser"),
        )
        self.processes.answer_json(
            ("awawa", "show", "@TASK.B12", "--json", str(self.worktree)),
            {"file": str(self.worktree / "corpus" / "tasks.awawa")},
        )
        self.processes.answer_corpus_change(self.worktree, ("corpus/tasks.awawa",), MESSAGE)
        self.processes.answer(("git", "push", "--quiet", "origin", "task/f0-parser/B12"))
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="d00d\n"
        )

    def declare_schema(self, schema: dict) -> None:
        self.processes.answer_json(("awawa", "show", "TASK", "--json", str(self.worktree)), schema)

    def create_demand(self, pr: int | None) -> TaskPromotionDemand:
        return TaskPromotionDemand(
            path=self.worktree,
            task="B12",
            pr=pr,
            environment={},
            attribution=("Co-Authored-By: Ada <ada@example.org>",),
        )

    def record_opened_pull_request(self, pr: int) -> None:
        append_event(
            self.runtime.paths,
            datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
            TaskPrOpened(project="oak", task="B12", wave="oak_w1", branch="task/f0-parser/B12", pr=pr, login="bot"),
        )

    def test_should_mark_the_task_implemented_and_delivered_by_its_pull_request(self):
        # Arrange
        self.declare_schema(DECLARED_SCHEMA)

        # Act
        promote_task(self.runtime, self.create_demand(42))

        # Assert
        self.assertEqual(
            (self.worktree / "corpus" / "tasks.awawa").read_text(encoding="utf-8"),
            'TASK B12\n\tTITLE "The parser"\n\tSTATUS implemented\n\tDELIVERED_BY 42\n\nTASK B13\n\tSTATUS todo\n',
        )

    def test_should_report_the_promotion_and_the_commit_it_pushed(self):
        # Arrange
        self.declare_schema(DECLARED_SCHEMA)

        # Act
        promoted = promote_task(self.runtime, self.create_demand(42))

        # Assert
        self.assertEqual(promoted, {"schema_version": 1, "project": "oak", "task": "B12", "pr": 42, "commit": "d00d"})

    def test_should_record_the_promotion_in_the_ledger(self):
        # Arrange
        self.declare_schema(DECLARED_SCHEMA)

        # Act
        promote_task(self.runtime, self.create_demand(42))

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries[-1].event.to_document(),
            {"project": "oak", "task": "B12", "pr": 42, "commit": "d00d"},
        )

    def test_should_promote_on_the_last_pull_request_the_ledger_records_for_the_task(self):
        # Arrange
        self.declare_schema(DECLARED_SCHEMA)
        self.record_opened_pull_request(41)
        self.record_opened_pull_request(42)

        # Act
        promoted = promote_task(self.runtime, self.create_demand(None))

        # Assert
        self.assertEqual(promoted["pr"], 42)

    def test_should_refuse_a_task_whose_pull_request_is_neither_named_nor_recorded(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            promote_task(self.runtime, self.create_demand(None))

        # Assert
        self.assertEqual(
            str(refusal.exception), "no pull request of @TASK.B12 is recorded in the ledger; name it with --pr"
        )

    def test_should_refuse_a_schema_that_declares_no_implemented_status(self):
        # Arrange
        self.declare_schema({"fields": [{"name": "FIELD", "atoms": ["STATUS", "draft|todo"]}]})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            promote_task(self.runtime, self.create_demand(42))

        # Assert
        self.assertEqual(str(refusal.exception), "the TASK schema of the corpus of oak declares no STATUS implemented")

    def test_should_refuse_a_schema_that_declares_no_delivering_pull_request(self):
        # Arrange
        self.declare_schema({"fields": [{"name": "FIELD", "atoms": ["STATUS", "todo|implemented"]}]})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            promote_task(self.runtime, self.create_demand(42))

        # Assert
        self.assertEqual(str(refusal.exception), "the TASK schema of the corpus of oak declares no DELIVERED_BY")
