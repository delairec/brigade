import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_created import MilestoneCreated
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.wave_started import WaveStarted
from brigade.tasks.open_task_pull_request import TaskPullRequestDemand, open_task_pull_request
from tests.unit.captures.take_screenshot import take_screenshot
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

WAVE_START = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)
WAVE_STARTED = WaveStarted(wave="oak_w1", project="oak", tasks=("B12",))
MILESTONE_BRANCH_CUT = MilestoneBranchCut(project="oak", milestone="F0", branch="integration/f0-parser", login=None)
TASK_FIELDS = (
    ("TYPE", "feat"),
    ("COMPONENT", "the parser"),
    ("TITLE", "The parser"),
    ("SPEC", "parses a line"),
    ("MILESTONE", "@MILESTONE.F0"),
)
FIX_FIELDS = (
    ("TYPE", "fix"),
    ("CORRECTS", "7"),
    ("CORRECTS", "9"),
    ("TITLE", "The parser"),
    ("SPEC", "parses a line"),
    ("MILESTONE", "@MILESTONE.F0"),
)
CORRECTED_PULL_REQUEST_OPENED = TaskPrOpened(
    project="oak", task="B3", wave="oak_w0", branch="feature/B3-the-lexer", pr=7, login="clauche-bot"
)
PULL_REQUEST_OF_ANOTHER_PROJECT_OPENED = TaskPrOpened(
    project="elm", task="E4", wave="elm_w1", branch="feature/E4-the-tree", pr=7, login="clauche-bot"
)
PASSING_CHECK = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "c0ffee",'
    ' "checks": [{"command": "python3 -m unittest", "passed": true, "duration_ms": 1200, "tail": []}]}'
)
CHECK_OF_ANOTHER_COMMIT = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "bead",'
    ' "checks": [{"command": "python3 -m unittest", "passed": true, "duration_ms": 1200, "tail": []}]}'
)
FAILED_CHECK = (
    '{"schema_version": 1, "project": "oak", "task": "B12", "head": "c0ffee",'
    ' "checks": [{"command": "ruff check .", "passed": false, "duration_ms": 30, "tail": []}]}'
)
OPENED_PULL_REQUEST = {"number": 42, "url": "https://github.com/acme/oak/pull/42"}


def create_forge(milestones: list[str]) -> ForgeDouble:
    return ForgeDouble(
        {
            "list_milestones": lambda request: {"titles": milestones},
            "create_milestone": lambda request: None,
            "open_pull_request": lambda request: OPENED_PULL_REQUEST,
        }
    )


class OpenTaskPullRequestTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        config_root = self.runtime.paths.config_root
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout="/srv/oak-b12\n")
        self.processes.answer(("git", "branch", "--show-current"), stdout="feature/B12-the-parser\n")
        self.processes.answer(
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"), stdout="/srv/oak/.git\n"
        )
        self.processes.answer_entities(config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"))})
        self.processes.answer_entities(
            config_root,
            "REQUEST",
            {"oak_1": (("PROJECT", "@PROJECT.oak"), ("BRANCH", "integration/f0-parser"))},
            ("PROJECT==@PROJECT.oak", "BRANCH==integration/f0-parser"),
        )
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}"), stdout="c0ffee\n"
        )
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "refs/remotes/origin/feature/B12-the-parser"), stdout="c0ffee\n"
        )
        self.processes.answer(
            (
                "git",
                "push",
                "--quiet",
                "--force-with-lease=feature/B12-the-parser:c0ffee",
                "origin",
                "feature/B12-the-parser",
            )
        )
        self.processes.answer_entity(Path("/srv/oak-b12"), "MILESTONE", "F0", (("TITLE", "Parser"),))
        append_event(self.runtime.paths, WAVE_START, MILESTONE_BRANCH_CUT)
        append_event(self.runtime.paths, WAVE_START, WAVE_STARTED)

    def record_check(self, check: str) -> None:
        record = self.root / "state" / "checks" / "oak" / "B12.json"
        record.parent.mkdir(parents=True)
        record.write_text(check, encoding="utf-8")

    def create_demand(self, forge: ForgeDouble) -> TaskPullRequestDemand:
        return TaskPullRequestDemand(
            path=Path("/srv/oak-b12"),
            task=None,
            subject="add the parser",
            forge=forge,
            environment={"GH_TOKEN": "t0ken"},
            login="clauche-bot",
            attribution=("Co-Authored-By: Ada <ada@example.org>",),
        )


class OpenTaskPullRequestInAnAreaTest(OpenTaskPullRequestTestCase):
    def test_should_read_the_task_and_its_milestone_in_the_area(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("MAIN", "main"), ("CORPUS", "brigade"), ("MODE", "area"))},
        )
        area = Path("/srv/oak-b12/brigade")
        self.processes.answer_entity(area, "TASK", "B12", TASK_FIELDS)
        self.processes.answer_entity(area, "MILESTONE", "F0", (("TITLE", "Parser"),))

        # Act
        opened = open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(opened["pr"], 42)
        self.assertIn(("awawa", "show", "@MILESTONE.F0", "--json", str(area)), self.processes.list_argvs())
        self.assertNotIn(("awawa", "show", "@MILESTONE.F0", "--json", "/srv/oak-b12"), self.processes.list_argvs())


class OpenTaskPullRequestTest(OpenTaskPullRequestTestCase):
    def setUp(self):
        super().setUp()
        self.record_check(PASSING_CHECK)

    def test_should_open_the_pull_request_of_the_task_into_the_branch_of_its_milestone(self):
        # Arrange
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)

        # Act
        opened = open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(
            opened,
            {
                "schema_version": 1,
                "project": "oak",
                "task": "B12",
                "branch": "feature/B12-the-parser",
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
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)
        forge = create_forge(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("open_pull_request"),
            [
                {
                    "repository": "/srv/oak-b12",
                    "base": "integration/f0-parser",
                    "branch": "feature/B12-the-parser",
                    "title": "feat(the-parser): add the parser (@TASK.B12)",
                    "body": "The parser\n"
                    "\n"
                    "## Acceptance criteria\n"
                    "\n"
                    "- parses a line\n"
                    "\n"
                    "## Checks of c0ffee\n"
                    "\n"
                    "- ok `python3 -m unittest` 1.2 s\n"
                    "\n"
                    "Co-Authored-By: Ada <ada@example.org>\n",
                    "milestone": "Parser",
                    "environment": {"GH_TOKEN": "t0ken"},
                }
            ],
        )

    def test_should_show_the_captures_of_the_checked_head_in_the_body_of_the_pull_request(self):
        # Arrange
        reference = {
            "name": "REFERENCE",
            "atoms": ['"artifact/parser.html"'],
            "fields": [{"name": "COVERS", "atoms": ['"parser"'], "fields": []}],
        }
        fields = [
            {"name": "TYPE", "atoms": ['"feat"'], "fields": []},
            {"name": "COMPONENT", "atoms": ['"the parser"'], "fields": []},
            {"name": "TITLE", "atoms": ['"The parser"'], "fields": []},
            {"name": "SPEC", "atoms": ['"parses a line"'], "fields": []},
            {"name": "MILESTONE", "atoms": ['"@MILESTONE.F0"'], "fields": []},
        ]
        self.processes.answer_json(
            ("awawa", "show", "@TASK.B12", "--json", "/srv/oak-b12"), {"fields": [*fields, reference]}
        )
        published = self.runtime.paths.state_root / "captures" / "oak" / "B12" / "c0ffee"
        published.mkdir(parents=True)
        (published / "section.md").write_text("## Captures\n\nEach page the task covers at c0ffee.\n\n")
        forge = create_forge(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertIn(
            "## Checks of c0ffee\n\n- ok `python3 -m unittest` 1.2 s\n\n## Captures\n\nEach page the task covers at c0ffee.\n\n",
            forge.list_requests("open_pull_request")[0]["body"],
        )

    def test_should_capture_the_checked_head_in_the_worktree_and_host_it_as_the_account_of_the_demand(self):
        # Arrange
        worktree = self.root / "oak-b12"
        (worktree / "artifact").mkdir(parents=True)
        (worktree / "artifact" / "parser.html").write_text('<html><head></head><section id="parser"></section></html>')
        self.processes.answer(("git", "rev-parse", "--show-toplevel"), stdout=f"{worktree}\n")
        self.processes.answer_entity(worktree, "MILESTONE", "F0", (("TITLE", "Parser"),))
        reference = {
            "name": "REFERENCE",
            "atoms": ['"artifact/parser.html"'],
            "fields": [{"name": "COVERS", "atoms": ['"parser"'], "fields": []}],
        }
        fields = [
            {"name": "TYPE", "atoms": ['"feat"'], "fields": []},
            {"name": "COMPONENT", "atoms": ['"the parser"'], "fields": []},
            {"name": "TITLE", "atoms": ['"The parser"'], "fields": []},
            {"name": "SPEC", "atoms": ['"parses a line"'], "fields": []},
            {"name": "MILESTONE", "atoms": ['"@MILESTONE.F0"'], "fields": []},
        ]
        self.processes.answer_json(
            ("awawa", "show", "@TASK.B12", "--json", str(worktree)), {"fields": [*fields, reference]}
        )
        self.processes.answer_json(
            ("awawa", "status", "--json", str(worktree)), {"entities": [{"type": "RECIPE", "name": "capture"}]}
        )
        self.processes.answer_json(
            ("awawa", "show", "@RECIPE.capture", "--json", str(worktree)),
            {
                "name": "capture",
                "fields": [
                    {"name": "SCHEMA_VERSION", "atoms": ['"1"'], "fields": []},
                    {
                        "name": "STEP",
                        "atoms": ['"command"'],
                        "fields": [
                            {"name": "ARGV", "atoms": ['"oak"'], "fields": []},
                            {"name": "ARGV", "atoms": ['"{page}"'], "fields": []},
                        ],
                    },
                ],
            },
        )
        self.processes.answer(("oak", "parser"), stdout=f"<html><body>{self.runtime.paths.home}/oak</body></html>")
        captures = self.runtime.paths.state_root / "captures" / "oak" / "B12" / "c0ffee"
        self.processes.answer_by(
            (
                "firefox",
                "--headless",
                "--no-remote",
                "--profile",
                str(captures / "profile"),
                "--window-size",
                "1440",
                "--screenshot",
                str(captures / "parser-delivered.png"),
                (captures / "parser-delivered.html").as_uri(),
            ),
            take_screenshot,
        )
        self.processes.answer_by(
            (
                "firefox",
                "--headless",
                "--no-remote",
                "--profile",
                str(captures / "profile"),
                "--window-size",
                "1440",
                "--screenshot",
                str(captures / "parser-reference.png"),
                f"{(captures / 'parser-reference.html').as_uri()}#parser",
            ),
            take_screenshot,
        )
        forge = ForgeDouble(
            {
                "list_milestones": lambda request: {"titles": ["Parser"]},
                "open_pull_request": lambda request: OPENED_PULL_REQUEST,
                "read_repository_visibility": lambda request: {"schema_version": 1, "public": True},
                "host_images": lambda request: {
                    "schema_version": 1,
                    "urls": ["https://gist/d.png", "https://gist/r.png"],
                },
            }
        )

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("host_images"),
            [
                {
                    "repository": str(worktree),
                    "environment": {"GH_TOKEN": "t0ken"},
                    "files": [str(captures / "parser-delivered.png"), str(captures / "parser-reference.png")],
                    "description": "captures of @TASK.B12",
                }
            ],
        )
        self.assertEqual((captures / "parser-delivered.html").read_text(), "<html><body>~/oak</body></html>")
        self.assertIn("Each page the task covers at c0ffee", forge.list_requests("open_pull_request")[0]["body"])

    def test_should_record_the_opened_pull_request_in_the_ledger(self):
        # Arrange
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)

        # Act
        open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(instant=WAVE_START, event=MILESTONE_BRANCH_CUT),
                LedgerEntry(instant=WAVE_START, event=WAVE_STARTED),
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=TaskPrOpened(
                        project="oak",
                        task="B12",
                        wave="oak_w1",
                        branch="feature/B12-the-parser",
                        pr=42,
                        login="clauche-bot",
                    ),
                ),
            ),
        )

    def test_should_open_the_body_on_each_pull_request_the_task_corrects(self):
        # Arrange
        append_event(self.runtime.paths, WAVE_START, CORRECTED_PULL_REQUEST_OPENED)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", FIX_FIELDS)
        forge = create_forge(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("open_pull_request")[0]["body"],
            "Corrects #7 (@TASK.B3)\n"
            "Corrects #9\n"
            "\n"
            "The parser\n"
            "\n"
            "## Acceptance criteria\n"
            "\n"
            "- parses a line\n"
            "\n"
            "## Checks of c0ffee\n"
            "\n"
            "- ok `python3 -m unittest` 1.2 s\n"
            "\n"
            "Co-Authored-By: Ada <ada@example.org>\n",
        )

    def test_should_name_no_task_for_a_pull_request_of_another_project_bearing_the_number_corrected(self):
        # Arrange
        append_event(self.runtime.paths, WAVE_START, PULL_REQUEST_OF_ANOTHER_PROJECT_OPENED)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", FIX_FIELDS)
        forge = create_forge(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("open_pull_request")[0]["body"].split("\n\n")[0], "Corrects #7\nCorrects #9"
        )

    def test_should_record_the_pull_requests_the_task_corrects_in_the_ledger(self):
        # Arrange
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", FIX_FIELDS)

        # Act
        open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(read_ledger(self.root / "state").entries[-1].event.corrects, (7, 9))

    def test_should_create_the_milestone_the_forge_lacks(self):
        # Arrange
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)
        forge = create_forge(["Printer"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("create_milestone"),
            [{"repository": "/srv/oak-b12", "environment": {"GH_TOKEN": "t0ken"}, "title": "Parser"}],
        )

    def test_should_record_the_milestone_it_created(self):
        # Arrange
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)

        # Act
        open_task_pull_request(self.runtime, self.create_demand(create_forge(["Printer"])))

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries[2],
            LedgerEntry(instant=FIXED_NOW, event=MilestoneCreated(project="oak", title="Parser", login="clauche-bot")),
        )

    def test_should_open_the_title_on_the_type_alone_for_a_task_with_no_component(self):
        # Arrange
        self.processes.answer_entity(
            Path("/srv/oak-b12"),
            "TASK",
            "B12",
            (("TYPE", "fix"), ("CORRECTS", "7"), ("TITLE", "The parser"), ("MILESTONE", "@MILESTONE.F0")),
        )

        # Act
        opened = open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(opened["title"], "fix: add the parser (@TASK.B12)")

    def test_should_push_the_branch_of_the_task_in_the_environment_of_the_demand(self):
        # Arrange
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)
        pushed_environments = []

        def record_push(request):
            pushed_environments.append(request.environment)
            return 0, "", ""

        self.processes.answer_by(
            (
                "git",
                "push",
                "--quiet",
                "--force-with-lease=feature/B12-the-parser:c0ffee",
                "origin",
                "feature/B12-the-parser",
            ),
            record_push,
        )

        # Act
        open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(pushed_environments, [{"GH_TOKEN": "t0ken"}])

    def test_should_open_on_the_milestone_the_forge_holds_without_creating_it(self):
        # Arrange
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)
        forge = create_forge(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(forge.list_operations(), ["list_milestones", "open_pull_request"])


class OpenTaskPullRequestWithNoMilestoneTest(OpenTaskPullRequestTestCase):
    def test_should_open_the_pull_request_of_a_task_naming_no_milestone_into_the_main_branch_without_milestone(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(
            Path("/srv/oak-b12"),
            "TASK",
            "B12",
            (("TYPE", "fix"), ("CORRECTS", "7"), ("TITLE", "The parser"), ("SPEC", "parses a line")),
        )
        forge = create_forge(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("open_pull_request"),
            [
                {
                    "repository": "/srv/oak-b12",
                    "base": "main",
                    "branch": "feature/B12-the-parser",
                    "title": "fix: add the parser (@TASK.B12)",
                    "body": "Corrects #7\n"
                    "\n"
                    "The parser\n"
                    "\n"
                    "## Acceptance criteria\n"
                    "\n"
                    "- parses a line\n"
                    "\n"
                    "## Checks of c0ffee\n"
                    "\n"
                    "- ok `python3 -m unittest` 1.2 s\n"
                    "\n"
                    "Co-Authored-By: Ada <ada@example.org>\n",
                    "milestone": None,
                    "environment": {"GH_TOKEN": "t0ken"},
                }
            ],
        )

    def test_should_create_no_milestone_on_the_forge_for_a_task_naming_none(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(
            Path("/srv/oak-b12"), "TASK", "B12", (("TYPE", "fix"), ("CORRECTS", "7"), ("TITLE", "The parser"))
        )
        forge = create_forge(["Parser"])

        # Act
        open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertEqual(forge.list_operations(), ["open_pull_request"])


class OpenTaskPullRequestRefusalTest(OpenTaskPullRequestTestCase):
    def setUp(self):
        super().setUp()
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", TASK_FIELDS)

    def test_should_neither_push_nor_open_nor_record_a_task_it_refuses(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(
            Path("/srv/oak-b12"), "TASK", "B12", (("TITLE", "The parser"), ("MILESTONE", "@MILESTONE.F0"))
        )
        forge = create_forge(["Parser"])

        # Act
        with self.assertRaises(BrigadeError):
            open_task_pull_request(self.runtime, self.create_demand(forge))

        # Assert
        self.assertNotIn(
            (
                "git",
                "push",
                "--quiet",
                "--force-with-lease=feature/B12-the-parser:c0ffee",
                "origin",
                "feature/B12-the-parser",
            ),
            self.processes.list_argvs(),
        )
        self.assertEqual(forge.list_operations(), [])
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(instant=WAVE_START, event=MILESTONE_BRANCH_CUT),
                LedgerEntry(instant=WAVE_START, event=WAVE_STARTED),
            ),
        )

    def test_should_refuse_a_task_whose_check_is_not_recorded(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(str(refusal.exception), "no check of @TASK.B12 is recorded; run brigade build check")

    def test_should_refuse_a_check_of_another_commit_than_head(self):
        # Arrange
        self.record_check(CHECK_OF_ANOTHER_COMMIT)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "the last check of @TASK.B12 is of bead, not of HEAD c0ffee; run brigade build check",
        )

    def test_should_refuse_a_failed_check(self):
        # Arrange
        self.record_check(FAILED_CHECK)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(
            str(refusal.exception), "the last check of @TASK.B12 failed on ruff check .; run brigade build check"
        )

    def test_should_refuse_a_fix_carrying_no_corrects(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", (("TYPE", "fix"), ("TITLE", "The parser")))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(
            str(refusal.exception), "@TASK.B12 is a fix carrying no CORRECTS, the pull request it corrects"
        )

    def test_should_refuse_a_task_with_no_type(self):
        # Arrange
        self.record_check(PASSING_CHECK)
        self.processes.answer_entity(Path("/srv/oak-b12"), "TASK", "B12", (("TITLE", "The parser"),))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            open_task_pull_request(self.runtime, self.create_demand(create_forge(["Parser"])))

        # Assert
        self.assertEqual(
            str(refusal.exception), "@TASK.B12 carries no TYPE, which the title of its pull request opens on"
        )
