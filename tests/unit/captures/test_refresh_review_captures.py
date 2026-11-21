import tempfile
import unittest
from pathlib import Path

from brigade.captures.refresh_review_captures import ReviewCaptureRefresh, refresh_review_captures
from brigade.recipes.recipe_places import BUILT_IN_RECIPES, RecipePlaces
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

HEAD = "4567def"
RESOLVE_HEAD = ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "HEAD^{commit}")
PUBLISHED_SECTION = (
    "## Captures\n\nEach page at 4567def.\n\n| Page | Delivered | Reference |\n|---|---|---|\n| tides | `d1` | `r1` |\n"
)
OLD_BODY = (
    "The tide table\n\n## Checks of 0123abc\n\n- ok `make` 1.0 s\n\n"
    "## Captures\n\nEach page at 0123abc.\n\n| Page | Delivered | Reference |\n|---|---|---|\n| tides | `d0` | `r0` |\n\n"
    "Co-Authored-By: Fake Client <fake@example.org>\n"
)
TIDES_TO_CAPTURE = {"reference": "artifact/index.html", "covers": "tides", "refusal": None, "captures": None}


class RefreshReviewCapturesTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.paths = create_test_paths(root)
        self.worktree = root / "worktree"
        self.published = self.paths.state_root / "captures" / "harbour" / "T7" / HEAD
        self.published.mkdir(parents=True)
        (self.published / "section.md").write_text(PUBLISHED_SECTION)
        (self.published / "tides-delivered-01.png").write_bytes(b"png")
        (self.published / "tides-reference-01.png").write_bytes(b"png")
        self.processes = ScriptedProcesses()
        self.processes.answer(RESOLVE_HEAD, stdout=f"{HEAD}\n")
        self.forge = ForgeDouble(
            {
                "read_pull_request": lambda request: {"pull_request": {"body": OLD_BODY}},
                "rewrite_pull_request_body": lambda request: {},
            }
        )
        self.equipped = 0

    def equip(self, pr: int | None = 42) -> ReviewCaptureRefresh:
        self.equipped += 1
        return ReviewCaptureRefresh(
            project="harbour",
            task="T7",
            worktree=self.worktree,
            places=RecipePlaces(None, self.worktree / "recipes", self.worktree / "machine", BUILT_IN_RECIPES),
            corpus=self.worktree,
            pr=pr,
            forge=self.forge,
            environment={"GH_TOKEN": "t0ken"},
        )

    def refresh(self, document: dict, equip=None) -> dict:
        runtime = create_test_runtime(self.paths, run_process=self.processes)
        return refresh_review_captures(runtime, document, self.equip if equip is None else equip)

    def test_should_name_the_captures_of_the_head_under_review_once_taken(self):
        # Act
        document = self.refresh({"head": HEAD, "references": [TIDES_TO_CAPTURE]})

        # Assert
        self.assertEqual(
            document["references"],
            [
                {
                    "reference": "artifact/index.html",
                    "covers": "tides",
                    "refusal": None,
                    "captures": {
                        "delivered": [str(self.published / "tides-delivered-01.png")],
                        "reference": [str(self.published / "tides-reference-01.png")],
                    },
                }
            ],
        )

    def test_should_put_the_captures_of_the_head_under_review_in_the_body_of_its_pull_request(self):
        # Act
        self.refresh({"head": HEAD, "references": [TIDES_TO_CAPTURE]})

        # Assert
        self.assertEqual(
            self.forge.list_requests("rewrite_pull_request_body"),
            [
                {
                    "repository": str(self.worktree),
                    "number": 42,
                    "body": "The tide table\n\n## Checks of 0123abc\n\n- ok `make` 1.0 s\n\n"
                    "## Captures\n\nEach page at 4567def.\n\n| Page | Delivered | Reference |\n|---|---|---|\n"
                    "| tides | `d1` | `r1` |\n\nCo-Authored-By: Fake Client <fake@example.org>\n",
                    "environment": {"GH_TOKEN": "t0ken"},
                }
            ],
        )

    def test_should_capture_nothing_from_a_worktree_at_another_head_than_the_one_under_review(self):
        # Arrange
        document = {"head": "89abcde", "references": [TIDES_TO_CAPTURE]}

        # Act
        refreshed = self.refresh(document)

        # Assert
        self.assertEqual(refreshed, document)
        self.assertEqual(self.forge.requests, [])

    def test_should_equip_nothing_when_every_page_of_the_head_is_captured_or_refused(self):
        # Arrange
        refused = {**TIDES_TO_CAPTURE, "refusal": "a REFERENCE is a repository path"}
        document = {"head": HEAD, "references": [refused]}

        # Act
        refreshed = self.refresh(document)

        # Assert
        self.assertEqual(refreshed, document)
        self.assertEqual(self.equipped, 0)

    def test_should_rewrite_no_body_for_a_task_with_no_pull_request(self):
        # Arrange
        no_pull_request = None

        # Act
        self.refresh({"head": HEAD, "references": [TIDES_TO_CAPTURE]}, lambda: self.equip(no_pull_request))

        # Assert
        self.assertEqual(self.forge.requests, [])
