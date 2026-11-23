import tempfile
import unittest
from pathlib import Path

from brigade.captures.capture_task_pages import CaptureDemand, capture_task_pages
from brigade.errors import ToolFailure
from brigade.recipes.recipe_places import BUILT_IN_RECIPES, RecipePlaces
from tests.unit.captures.build_png import build_png
from tests.unit.captures.take_screenshot import take_screenshot
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
TIDES = {"reference": "artifact/harbour/index.html", "covers": "tides", "reads": None}


ONE_GREY_PIXEL_ROW = b"\x00\x07\x07\x07\xff"
PAGE_ONE_ROW_TALLER_THAN_A_SLICE = build_png(1, 2001, ONE_GREY_PIXEL_ROW * 2001)


def _take_a_screenshot_one_row_taller_than_a_slice(request) -> tuple[int, str, str]:
    Path(request.argv[request.argv.index("--screenshot") + 1]).write_bytes(PAGE_ONE_ROW_TALLER_THAN_A_SLICE)
    return 0, "", ""


def _time_out(request) -> tuple[int, str, str]:
    raise ToolFailure("firefox --screenshot timed out after 300 s")


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
            f"{(self.directory / 'tides-reference.html').as_uri()}#tides",
        )
        self.processes.answer_by(self.delivered_capture, self.run_firefox)
        self.processes.answer_by(self.reference_capture, self.run_firefox)

    def run_firefox(self, request) -> tuple[int, str, str]:
        self.firefox_runs.append(request.argv)
        return take_screenshot(request)

    def fail_the_reference_screenshot(self, respond) -> None:
        self.processes.answer_by(self.reference_capture, respond)

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
                        "delivered_slices": [str(self.directory / "tides-delivered-01.png")],
                        "reference_slices": [str(self.directory / "tides-reference-01.png")],
                    }
                ],
                "skipped": [],
            },
        )

    def test_should_cut_a_page_taller_than_2000_px_into_slices_of_2000_px(self):
        # Arrange
        self.declare_the_recipe()
        self.processes.answer_by(self.delivered_capture, _take_a_screenshot_one_row_taller_than_a_slice)

        # Act
        captured = self.capture([TIDES])

        # Assert
        self.assertEqual(
            captured["pages"][0]["delivered_slices"],
            [str(self.directory / "tides-delivered-01.png"), str(self.directory / "tides-delivered-02.png")],
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
                [{"reference": "https://example.org/harbour", "covers": "tides", "reads": None}],
                ["https://example.org/harbour: a REFERENCE is a repository path, a URL is not captured"],
            ),
            (
                "a reference that is no HTML page",
                [{"reference": "docs/harbour.pdf", "covers": "tides", "reads": None}],
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

    def test_should_say_why_a_page_whose_recipe_fails_is_not_captured(self):
        # Arrange
        self.declare_the_recipe()
        self.processes.answer(("harbour", "render", "tides"), exit_code=3, stderr="no view serves tides\n")

        # Act
        captured = self.capture([TIDES])

        # Assert
        self.assertEqual(
            captured,
            {
                "schema_version": 1,
                "directory": str(self.directory),
                "pages": [],
                "skipped": ["tides: the recipe capture failed with exit 3: no view serves tides"],
            },
        )

    def test_should_run_no_screenshot_for_a_page_whose_recipe_fails(self):
        # Arrange
        self.declare_the_recipe()
        self.processes.answer(("harbour", "render", "tides"), exit_code=3, stderr="no view serves tides\n")

        # Act
        self.capture([TIDES])

        # Assert
        self.assertEqual(self.firefox_runs, [])

    def test_should_say_why_a_reference_it_cannot_read_or_a_section_it_cannot_find_is_not_captured(self):
        # Arrange
        rows = [
            (
                "a coverage naming no section of the reference",
                {"reference": "artifact/harbour/index.html", "covers": "docks", "reads": None},
                "artifact/harbour/index.html: no section of the reference has the id docks",
            ),
            (
                "a coverage that is no section id",
                {"reference": "artifact/harbour/index.html", "covers": 'tides"],x', "reads": None},
                'artifact/harbour/index.html: the COVERS tides"],x is not a section id',
            ),
            (
                "a reference climbing out of the repository",
                {"reference": "../outside.html", "covers": "tides", "reads": None},
                "../outside.html: a REFERENCE is a path inside the repository",
            ),
            (
                "an absolute reference",
                {"reference": "/etc/harbour.html", "covers": "tides", "reads": None},
                "/etc/harbour.html: a REFERENCE is a path inside the repository",
            ),
            (
                "a reference absent from the repository",
                {"reference": "artifact/missing.html", "covers": "tides", "reads": None},
                "artifact/missing.html: no such file in the repository",
            ),
        ]
        self.declare_the_recipe()
        for case, reference, expected_reason in rows:
            with self.subTest(case=case):
                # Act
                captured = self.capture([reference])

                # Assert
                self.assertEqual(captured["skipped"], [expected_reason])

    def test_should_capture_the_page_the_last_step_of_the_recipe_prints(self):
        # Arrange
        self.places.project_directory.mkdir(parents=True)
        (self.places.project_directory / "capture.toml").write_text(
            'schema_version = 1\nname = "capture"\ndescription = "a page of the harbour as delivered"\n'
            '[[steps]]\nkind = "command"\nargv = ["harbour", "build"]\n'
            '[[steps]]\nkind = "command"\nargv = ["harbour", "render", "{page}"]\n'
        )
        self.processes.answer(("harbour", "build"), stdout="built")

        # Act
        self.capture([TIDES])

        # Assert
        self.assertEqual((self.directory / "tides-delivered.html").read_text(), "<html><body>Tides of ~</body></html>")

    def test_should_run_the_recipe_in_the_worktree(self):
        # Arrange
        self.declare_the_recipe()

        # Act
        self.capture([TIDES])

        # Assert
        self.assertEqual(self.processes.requests[0].cwd, str(self.worktree))

    def test_should_remove_the_firefox_profile_once_the_page_is_captured(self):
        # Arrange
        self.declare_the_recipe()

        # Act
        self.capture([TIDES])

        # Assert
        self.assertFalse((self.directory / "profile").exists())

    def test_should_say_why_a_page_whose_screenshot_fails_is_not_captured(self):
        # Arrange
        rows = [
            (
                "a screenshot exiting non-zero",
                lambda request: (1, "", "no display in /home/sailor\n"),
                "tides: firefox failed with exit 1 on tides-reference.html: no display in ~",
            ),
            (
                "a screenshot timed out",
                _time_out,
                "tides: firefox --screenshot timed out after 300 s",
            ),
            (
                "a screenshot writing no image",
                lambda request: (0, "", ""),
                "tides: firefox wrote no tides-reference.png",
            ),
        ]
        self.declare_the_recipe()
        for case, respond, expected_reason in rows:
            with self.subTest(case=case):
                self.fail_the_reference_screenshot(respond)

                # Act
                captured = self.capture([TIDES])

                # Assert
                self.assertEqual(
                    captured,
                    {"schema_version": 1, "directory": str(self.directory), "pages": [], "skipped": [expected_reason]},
                )

    def test_should_remove_the_firefox_profile_of_a_page_whose_screenshot_fails(self):
        # Arrange
        self.declare_the_recipe()
        self.fail_the_reference_screenshot(lambda request: (1, "", "no display\n"))

        # Act
        self.capture([TIDES])

        # Assert
        self.assertFalse((self.directory / "profile").exists())

    def test_should_capture_no_section_its_task_judges_by_reading_a_file(self):
        # Arrange
        self.declare_the_recipe()
        (self.worktree / "harbour").mkdir()
        (self.worktree / "harbour" / "harbour.css").write_text("section#tides {}\n")
        foundation = {"reference": "artifact/harbour/index.html", "covers": "tides", "reads": "harbour/harbour.css"}

        # Act
        captured = self.capture([foundation])

        # Assert
        self.assertEqual(
            captured["skipped"],
            ["artifact/harbour/index.html: the section tides is judged by reading harbour/harbour.css: no capture"],
        )

    def test_should_say_that_a_read_naming_no_file_of_the_repository_cannot_be_judged(self):
        # Arrange
        self.declare_the_recipe()
        (self.worktree.parent / f"{self.worktree.name}-outside.css").write_text("section#tides {}\n")
        self.addCleanup((self.worktree.parent / f"{self.worktree.name}-outside.css").unlink)
        for case, read in [
            ("a file absent from the repository", "harbour/absent.css"),
            ("a URL", "https://example.org/harbour.css"),
            ("a file outside the repository", f"../{self.worktree.name}-outside.css"),
        ]:
            with self.subTest(case=case):
                foundation = {"reference": "artifact/harbour/index.html", "covers": "tides", "reads": read}

                # Act
                captured = self.capture([foundation])

                # Assert
                self.assertEqual(
                    captured["skipped"],
                    [f"artifact/harbour/index.html: the READ {read} names no file of the repository: no capture"],
                )

    def test_should_run_every_step_of_the_recipe_in_its_order(self):
        # Arrange
        self.places.project_directory.mkdir(parents=True)
        (self.places.project_directory / "capture.toml").write_text(
            'schema_version = 1\nname = "capture"\ndescription = "a page of the harbour as delivered"\n'
            '[[steps]]\nkind = "command"\nargv = ["harbour", "build"]\n'
            '[[steps]]\nkind = "command"\nargv = ["harbour", "render", "{page}"]\n'
        )
        self.processes.answer(("harbour", "build"), stdout="built")

        # Act
        self.capture([TIDES])

        # Assert
        self.assertEqual(self.processes.list_argvs()[:2], [("harbour", "build"), ("harbour", "render", "tides")])
