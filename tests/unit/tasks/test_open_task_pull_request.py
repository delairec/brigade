import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.wave_started import WaveStarted
from brigade.tasks.open_task_pull_request import TaskPullRequestDemand, open_task_pull_request
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

TASK_FIELDS = (
    ("TYPE", "feat"),
    ("COMPONENT", "the parser"),
    ("TITLE", "The parser"),
    ("SPEC", "parses a line"),
    ("MILESTONE", "@MILESTONE.F0"),
)
PASSING_CHECK = {
    "schema_version": 1,
    "project": "oak",
    "task": "B12",
    "head": "c0ffee",
    "checks": [{"command": "python3 -m unittest", "passed": True, "duration_ms": 1200, "tail": []}],
}


class ForgeDouble:
    def __init__(self, milestones: list[str]):
        self._milestones = milestones
        self.created = []
        self.opened = []

    def list_milestones(self, request: dict, runtime) -> dict:
        return {"titles": self._milestones}

    def create_milestone(self, request: dict, runtime) -> None:
        self.created.append(request)

    def open_pull_request(self, request: dict, runtime) -> dict:
        self.opened.append(request)
        return {"number": 42, "url": "https://github.com/acme/oak/pull/42"}


class OpenTaskPullRequestFixture(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        config_root = self.runtime.paths.config_root
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout="/srv/oak-b12\n")
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
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="c0ffee\n"
        )
        self.processes.answer(("git", "push", "--quiet", "origin", "task/f0-parser/B12"))
        self.processes.answer_entity(Path("/srv/oak-b12"), "MILESTONE", "F0", (("TITLE", "Parser"),))
        append_event(
            self.runtime.paths,
            datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
            WaveStarted(wave="oak_w1", project="oak", branch="integration/f0-parser", tasks=("B12",)),
        )

    def record_check(self, check: dict) -> None:
        record = self.root / "state" / "checks" / "oak" / "B12.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps(check), encoding="utf-8")

    def create_demand(self, forge: ForgeDouble, subject: str | None = "add the parser") -> TaskPullRequestDemand:
        return TaskPullRequestDemand(
            path=Path("/srv/oak-b12"),
            task=None,
            subject=subject,
            forge=forge,
            environment={"GH_TOKEN": "t0ken"},
            login="clauche-bot",
            attribution=("Co-Authored-By: Ada <ada@example.org>",),
        )


class OpenTaskPullRequestTest(OpenTaskPullRequestFixture):
    def test_should_open_the_pull_request_of_the_task_on_the_branch_of_its_wave(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)

        # Act
        opened = open_task_pull_request(self.runtime, self.create_demand(ForgeDouble(["Parser"])))

        # Assert
        self.assertEqual(
            opened,
            {
                "schema_version": 1,
                "project": "oak",
                "task": "B12",
                "branch": "task/f0-parser/B12",
                "base": "integration/f0-parser",
                "title": "feat(the-parser): add the parser (@TASK.B12)",
                "milestone": "Parser",
                "pr": 42,
                "url": "https://github.com/acme/oak/pull/42",
                "login": "clauche-bot",
            },
        )

    def test_should_describe_the_task_and_its_checks_in_the_body_of_the_pull_request(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)
        forge = ForgeDouble(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            forge.opened[0]["body"],
            "The parser\n\n## Acceptance criteria\n\n- parses a line\n\n## Checks of c0ffee\n\n"
            "- pass `python3 -m unittest` 1.2 s\n\nCo-Authored-By: Ada <ada@example.org>\n",
        )

    def test_should_record_the_opened_pull_request_in_the_ledger(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)

        # Act
        open_task_pull_request(self.runtime, self.create_demand(ForgeDouble(["Parser"])))

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries[-1].event.to_document(),
            {
                "project": "oak",
                "task": "B12",
                "wave": "oak_w1",
                "branch": "task/f0-parser/B12",
                "pr": 42,
                "login": "clauche-bot",
            },
        )

    def test_should_create_the_milestone_the_forge_lacks_and_record_it(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)
        forge = ForgeDouble(["Printer"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            (forge.created, read_ledger(self.root / "state").entries[1].event.to_document()),
            (
                [{"repository": "/srv/oak-b12", "environment": {"GH_TOKEN": "t0ken"}, "title": "Parser"}],
                {"project": "oak", "title": "Parser", "login": "clauche-bot"},
            ),
        )

    def test_should_open_the_title_on_the_type_alone_for_a_task_with_no_component(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(
            Path("/srv/oak-b12"),
            "TASK",
            "B12",
            (("TYPE", "fix"), ("TITLE", "The parser"), ("MILESTONE", "@MILESTONE.F0")),
        )

        # Act
        opened = open_task_pull_request(self.runtime, self.create_demand(ForgeDouble(["Parser"])))

        # Assert
        self.assertEqual(opened["title"], "fix: add the parser (@TASK.B12)")


class OpenTaskPullRequestRefusalTest(OpenTaskPullRequestFixture):
    def read_refusal(self) -> str:
        with self.assertRaises(BrigadeError) as refusal:
            open_task_pull_request(self.runtime, self.create_demand(ForgeDouble(["Parser"])))
        return str(refusal.exception)

    def test_should_refuse_a_task_whose_check_is_not_recorded(self):
        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "no check of @TASK.B12 is recorded; run brigade task check")

    def test_should_refuse_a_check_of_another_commit_than_head(self):
        # Arrange
        self.record_check({**PASSING_CHECK, "head": "bead"})

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "the last check of @TASK.B12 is of bead, not of HEAD c0ffee; run brigade task check")

    def test_should_refuse_a_failed_check(self):
        # Arrange
        self.record_check(
            {**PASSING_CHECK, "checks": [{"command": "ruff check .", "passed": False, "duration_ms": 30, "tail": []}]}
        )

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "the last check of @TASK.B12 failed on ruff check .; run brigade task check")

    def test_should_refuse_a_task_with_no_type(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", (("TITLE", "The parser"),))

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "@TASK.B12 carries no TYPE, which the title of its pull request opens on")

    def test_should_refuse_a_task_with_no_milestone(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", (("TYPE", "feat"), ("TITLE", "The parser")))

        # Act
        message = self.read_refusal()

        # Assert
        self.assertEqual(message, "@TASK.B12 carries no MILESTONE, whose TITLE names the milestone of its pull request")
