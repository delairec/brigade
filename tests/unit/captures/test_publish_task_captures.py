import json
import tempfile
import unittest
from pathlib import Path

from brigade.captures.publish_task_captures import CapturePublication, publish_task_captures
from brigade.recipes.recipe_places import BUILT_IN_RECIPES, RecipePlaces
from tests.unit.captures.take_screenshot import take_screenshot
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

CAPTURE_RECIPE = (
    'schema_version = 1\nname = "capture"\ndescription = "a page of the harbour as delivered"\n'
    '[[steps]]\nkind = "command"\nargv = ["harbour", "render", "{page}"]\n'
)
BOT_ENVIRONMENT = {"GH_TOKEN": "token-of-octo-bot"}
NO_FIELD = []
THE_FORGE_OF_THE_PROJECT = object()
NO_FORGE = None


def _host_at_the_gist(request: dict) -> dict:
    return {
        "schema_version": 1,
        "urls": ["https://gist.example/tides-delivered.png", "https://gist.example/tides-reference.png"],
    }


def _say_public(request: dict) -> dict:
    return {"schema_version": 1, "public": True}


def _say_private(request: dict) -> dict:
    return {"schema_version": 1, "public": False}


TIDES_REFERENCE = [
    {
        "name": "REFERENCE",
        "atoms": ['"artifact/index.html"'],
        "fields": [{"name": "COVERS", "atoms": ['"tides"'], "fields": []}],
    }
]


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
        self.forge = ForgeDouble({"host_images": _host_at_the_gist, "read_repository_visibility": _say_public})
        profile = str(self.directory / "profile")
        self.processes.answer_by(
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
            ),
            take_screenshot,
        )
        self.processes.answer_by(
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
                f"{(self.directory / 'tides-reference.html').as_uri()}#tides",
            ),
            take_screenshot,
        )

    def show_the_task(self, fields: list[dict]) -> None:
        self.processes.answer(
            ("awawa", "show", "@TASK.T7", "--json", str(self.worktree)), stdout=json.dumps({"fields": fields})
        )

    def publish(self, forge: object = THE_FORGE_OF_THE_PROJECT) -> str:
        publication = CapturePublication(
            worktree=self.worktree,
            places=self.places,
            task="T7",
            corpus=self.worktree,
            directory=self.directory,
            forge=self.forge if forge is THE_FORGE_OF_THE_PROJECT else forge,
            environment=BOT_ENVIRONMENT,
            home="/home/sailor",
            head="0123abc",
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

    def test_should_host_nothing_and_name_the_local_captures_for_a_private_repository(self):
        # Arrange
        self.show_the_task(TIDES_REFERENCE)
        forge = ForgeDouble({"read_repository_visibility": _say_private})

        # Act
        section = self.publish(forge)

        # Assert
        self.assertIn(f"| tides | `{self.directory / 'tides-delivered.png'}` |", section)
        self.assertEqual(forge.list_operations(), ["read_repository_visibility"])

    def test_should_ask_the_visibility_of_the_repository_with_the_environment_of_the_forge_account(self):
        # Arrange
        self.show_the_task(TIDES_REFERENCE)

        # Act
        self.publish()

        # Assert
        self.assertEqual(
            self.forge.list_requests("read_repository_visibility"),
            [{"repository": str(self.worktree), "environment": BOT_ENVIRONMENT}],
        )

    def test_should_host_nothing_for_a_project_acting_through_no_forge(self):
        # Arrange
        self.show_the_task(TIDES_REFERENCE)

        # Act
        section = self.publish(NO_FORGE)

        # Assert
        self.assertIn("Nothing is hosted", section)

    def test_should_answer_the_section_already_published_for_the_head_without_capturing_or_hosting_again(self):
        # Arrange
        self.show_the_task(TIDES_REFERENCE)
        first = self.publish()
        self.processes.requests.clear()
        self.forge.requests.clear()

        # Act
        second = self.publish()

        # Assert
        self.assertEqual(second, first)
        self.assertEqual(self.processes.requests, [])
        self.assertEqual(self.forge.requests, [])
