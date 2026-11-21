import tempfile
import unittest
from pathlib import Path

from brigade.captures.capture_task_pages import CaptureDemand, capture_task_pages
from brigade.recipes.recipe_places import BUILT_IN_RECIPES, RecipePlaces
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

HOME = "/home/sailor"
CAPTURE_RECIPE = (
    'schema_version = 1\nname = "capture"\ndescription = "a page of the harbour as delivered"\n'
    '[[steps]]\nkind = "command"\nargv = ["harbour", "render", "{page}"]\n'
)
REFERENCE_PAGE = (
    "<html><head><title>harbour</title></head><body>\n"
    '<section class="page" id="tides" data-page hidden>Tides read in /home/sailor/harbour</section>\n'
    '<section class="page" id="ports" data-page>Ports</section>\n'
    "</body></html>\n"
)
DELIVERED_PAGE = "<html><body>Tides of /home/sailor</body></html>"
TIDES = {"reference": "artifact/harbour/index.html", "covers": "tides"}


class CaptureTaskPagesTest(unittest.TestCase):
    def setUp(self):
        self.worktree = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.directory = self.worktree / "captures"
        (self.worktree / "artifact" / "harbour").mkdir(parents=True)
        (self.worktree / "artifact" / "harbour" / "index.html").write_text(REFERENCE_PAGE)
        self.places = RecipePlaces(
            project_corpus=None,
            project_directory=self.worktree / ".brigade" / "recipes",
            machine_directory=self.worktree / "machine",
            built_ins=BUILT_IN_RECIPES,
        )
        self.processes = ScriptedProcesses()
        self.processes.answer(("harbour", "render", "tides"), stdout=DELIVERED_PAGE)
        self.firefox_runs = []
        profile = str(self.directory / "profile")
        self.delivered_capture = (
            "firefox",
            "--headless",
            "--no-remote",
            "--profile",
            profile,
            "--window-size",
            "1440",
            "--screenshot",
            str(self.directory / "tides-delivered.png"),
            (self.directory / "tides-delivered.html").as_uri(),
        )
        self.reference_capture = (
            "firefox",
            "--headless",
            "--no-remote",
            "--profile",
            profile,
            "--window-size",
            "1440",
            "--screenshot",
            str(self.directory / "tides-reference.png"),
            (self.directory / "tides-reference.html").as_uri(),
        )
        self.processes.answer_by(self.delivered_capture, self.run_firefox)
        self.processes.answer_by(self.reference_capture, self.run_firefox)

    def run_firefox(self, request) -> tuple[int, str, str]:
        self.firefox_runs.append(request.argv)
        return 0, "", ""

    def declare_the_recipe(self) -> None:
        self.places.project_directory.mkdir(parents=True)
        (self.places.project_directory / "capture.toml").write_text(CAPTURE_RECIPE)

    def capture(self, references: list[dict]) -> dict:
        demand = CaptureDemand(
            worktree=self.worktree, places=self.places, references=references, directory=self.directory, home=HOME
        )
        return capture_task_pages(create_test_runtime(run_process=self.processes), demand)

    def test_should_name_the_delivered_and_the_reference_capture_of_each_covered_page(self):
        # Arrange
        self.declare_the_recipe()

        # Act
        captured = self.capture([TIDES])

        # Assert
        self.assertEqual(
            captured,
            {
                "schema_version": 1,
                "directory": str(self.directory),
                "pages": [
                    {
                        "page": "tides",
                        "delivered": str(self.directory / "tides-delivered.png"),
                        "reference": str(self.directory / "tides-reference.png"),
                    }
                ],
                "skipped": [],
            },
        )

    def test_should_render_the_delivered_page_with_the_recipe_the_home_directory_shown_as_a_tilde(self):
        # Arrange
        self.declare_the_recipe()

        # Act
        self.capture([TIDES])

        # Assert
        self.assertEqual((self.directory / "tides-delivered.html").read_text(), "<html><body>Tides of ~</body></html>")

    def test_should_show_the_reference_with_only_the_section_its_coverage_names(self):
        # Arrange
        self.declare_the_recipe()

        # Act
        self.capture([TIDES])

        # Assert
        self.assertEqual(
            (self.directory / "tides-reference.html").read_text(),
            "<html><head><title>harbour</title>"
            "<style>section[id]:not(#tides){display:none!important}</style></head><body>\n"
            '<section class="page" id="tides" data-page>Tides read in ~/harbour</section>\n'
            '<section class="page" id="ports" data-page>Ports</section>\n'
            "</body></html>\n",
        )

    def test_should_capture_each_page_with_headless_firefox_one_after_the_other(self):
        # Arrange
        self.declare_the_recipe()

        # Act
        self.capture([TIDES])

        # Assert
        self.assertEqual(self.firefox_runs, [self.delivered_capture, self.reference_capture])

    def test_should_say_why_a_reference_is_not_captured(self):
        # Arrange
        rows = [
            ("a task citing no reference", [], ["the task carries no REFERENCE: no capture"]),
            (
                "a reference that is a URL",
                [{"reference": "https://example.org/harbour", "covers": "tides"}],
                ["https://example.org/harbour: a REFERENCE is a repository path, a URL is not captured"],
            ),
            (
                "a reference that is no HTML page",
                [{"reference": "docs/harbour.pdf", "covers": "tides"}],
                ["docs/harbour.pdf: brigade renders an HTML reference only"],
            ),
        ]
        self.declare_the_recipe()
        for case, references, expected_reasons in rows:
            with self.subTest(case=case):
                # Act
                captured = self.capture(references)

                # Assert
                self.assertEqual(
                    captured,
                    {"schema_version": 1, "directory": str(self.directory), "pages": [], "skipped": expected_reasons},
                )

    def test_should_say_that_a_project_declaring_no_recipe_capture_has_no_capture(self):
        # Act
        captured = self.capture([TIDES])

        # Assert
        self.assertEqual(
            captured,
            {
                "schema_version": 1,
                "directory": str(self.directory),
                "pages": [],
                "skipped": ["the project declares no recipe capture: no capture"],
            },
        )
