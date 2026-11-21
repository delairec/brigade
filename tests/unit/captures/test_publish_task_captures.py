import json
import tempfile
import unittest
from pathlib import Path

from brigade.captures.publish_task_captures import CapturePublication, publish_task_captures
from brigade.recipes.recipe_places import BUILT_IN_RECIPES, RecipePlaces
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

CAPTURE_RECIPE = (
    'schema_version = 1\nname = "capture"\ndescription = "a page of the harbour as delivered"\n'
    '[[steps]]\nkind = "command"\nargv = ["harbour", "render", "{page}"]\n'
)
BOT_ENVIRONMENT = {"GH_TOKEN": "token-of-octo-bot"}
NO_FIELD = []


def _host_at_the_gist(request: dict) -> dict:
    return {
        "schema_version": 1,
        "urls": ["https://gist.example/tides-delivered.png", "https://gist.example/tides-reference.png"],
    }


class PublishTaskCapturesTest(unittest.TestCase):
    def setUp(self):
        self.worktree = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.directory = self.worktree / "captures"
        (self.worktree / "artifact").mkdir()
        (self.worktree / "artifact" / "index.html").write_text('<html><head></head><section id="tides"></section>')
        recipes = self.worktree / ".brigade" / "recipes"
        recipes.mkdir(parents=True)
        (recipes / "capture.toml").write_text(CAPTURE_RECIPE)
        self.places = RecipePlaces(
            project_corpus=None,
            project_directory=recipes,
            machine_directory=self.worktree / "machine",
            built_ins=BUILT_IN_RECIPES,
        )
        self.processes = ScriptedProcesses()
        self.processes.answer(("harbour", "render", "tides"), stdout="<html><body>Tides</body></html>")
        self.forge = ForgeDouble({"host_images": _host_at_the_gist})
        profile = str(self.directory / "profile")
        self.processes.answer(
            (
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
        )
        self.processes.answer(
            (
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
        )

    def show_the_task(self, fields: list[dict]) -> None:
        self.processes.answer(
            ("awawa", "show", "@TASK.T7", "--json", str(self.worktree)), stdout=json.dumps({"fields": fields})
        )

    def publish(self) -> str:
        publication = CapturePublication(
            worktree=self.worktree,
            places=self.places,
            task="T7",
            corpus=self.worktree,
            directory=self.directory,
            forge=self.forge,
            environment=BOT_ENVIRONMENT,
            home="/home/sailor",
        )
        return publish_task_captures(create_test_runtime(run_process=self.processes), publication)

    def test_should_show_each_covered_page_beside_its_reference_at_the_addresses_the_forge_hosts_them(self):
        # Arrange
        self.show_the_task(
            [
                {
                    "name": "REFERENCE",
                    "atoms": ['"artifact/index.html"'],
                    "fields": [{"name": "COVERS", "atoms": ['"tides"'], "fields": []}],
                }
            ]
        )

        # Act
        section = self.publish()

        # Assert
        self.assertIn(
            "| tides | ![tides delivered](https://gist.example/tides-delivered.png)"
            " | ![tides reference](https://gist.example/tides-reference.png) |\n",
            section,
        )

    def test_should_host_the_captures_with_the_environment_of_the_forge_account(self):
        # Arrange
        self.show_the_task(
            [
                {
                    "name": "REFERENCE",
                    "atoms": ['"artifact/index.html"'],
                    "fields": [{"name": "COVERS", "atoms": ['"tides"'], "fields": []}],
                }
            ]
        )

        # Act
        self.publish()

        # Assert
        self.assertEqual(
            self.forge.list_requests("host_images"),
            [
                {
                    "repository": str(self.worktree),
                    "environment": BOT_ENVIRONMENT,
                    "files": [str(self.directory / "tides-delivered.png"), str(self.directory / "tides-reference.png")],
                    "description": "captures of @TASK.T7",
                }
            ],
        )

    def test_should_add_no_section_and_host_nothing_for_a_task_citing_no_reference(self):
        # Arrange
        self.show_the_task(NO_FIELD)

        # Act
        section = self.publish()

        # Assert
        self.assertEqual(section, "")
        self.assertEqual(self.forge.list_operations(), [])

    def test_should_add_no_section_and_host_nothing_when_no_page_is_captured(self):
        # Arrange
        self.show_the_task(
            [
                {
                    "name": "REFERENCE",
                    "atoms": ['"https://example.org/harbour"'],
                    "fields": [{"name": "COVERS", "atoms": ['"tides"'], "fields": []}],
                }
            ]
        )

        # Act
        section = self.publish()

        # Assert
        self.assertEqual(section, "")
        self.assertEqual(self.forge.list_operations(), [])
