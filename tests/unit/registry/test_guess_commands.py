import tempfile
import unittest
from pathlib import Path

from brigade.registry.guess_commands import CommandGuess, guess_commands

ALL_SCRIPTS = '{"scripts": {"typecheck": "tsc", "build": "vite", "lint": "eslint .", "test": "vitest"}}'
TEST_SCRIPT = '{"scripts": {"test": "vitest"}}'
NO_SCRIPTS = "{}"
PYTEST_TABLE = "[tool.pytest.ini_options]\naddopts = '-q'\n"
NO_PYTEST_TABLE = "[project]\nname = 'app'\n"


def create_files(root: Path, files: dict) -> None:
    for relative_path, content in files.items():
        file = root / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)


class GuessCommandsTest(unittest.TestCase):
    def test_should_guess_the_commands_of_a_package_json(self):
        rows = [
            (
                "npm with a lockfile",
                {"package.json": ALL_SCRIPTS, "package-lock.json": "{}"},
                CommandGuess(
                    configurations=("package.json",),
                    acceptance=("npm run test", "npm run lint", "npm run typecheck"),
                    setup=("npm ci",),
                ),
            ),
            (
                "npm without a lockfile",
                {"package.json": TEST_SCRIPT},
                CommandGuess(configurations=("package.json",), acceptance=("npm run test",), setup=("npm install",)),
            ),
            (
                "bun.lock",
                {"package.json": TEST_SCRIPT, "bun.lock": ""},
                CommandGuess(
                    configurations=("package.json",),
                    acceptance=("bun run test",),
                    setup=("bun install --frozen-lockfile",),
                ),
            ),
            (
                "bun.lockb",
                {"package.json": TEST_SCRIPT, "bun.lockb": ""},
                CommandGuess(
                    configurations=("package.json",),
                    acceptance=("bun run test",),
                    setup=("bun install --frozen-lockfile",),
                ),
            ),
            (
                "pnpm",
                {"package.json": TEST_SCRIPT, "pnpm-lock.yaml": ""},
                CommandGuess(
                    configurations=("package.json",),
                    acceptance=("pnpm run test",),
                    setup=("pnpm install --frozen-lockfile",),
                ),
            ),
            (
                "yarn",
                {"package.json": TEST_SCRIPT, "yarn.lock": ""},
                CommandGuess(
                    configurations=("package.json",),
                    acceptance=("yarn run test",),
                    setup=("yarn install --frozen-lockfile",),
                ),
            ),
            (
                "no script",
                {"package.json": NO_SCRIPTS},
                CommandGuess(configurations=("package.json",), acceptance=(), setup=("npm install",)),
            ),
        ]
        for case, files, expected in rows:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                # Arrange
                create_files(Path(root), files)

                # Act
                guess = guess_commands(Path(root))

                # Assert
                self.assertEqual(guess, expected)

    def test_should_guess_the_commands_of_a_python_project(self):
        rows = [
            (
                "pyproject.toml without pytest",
                {"pyproject.toml": NO_PYTEST_TABLE},
                CommandGuess(configurations=("Python",), acceptance=("python3 -m unittest",), setup=()),
            ),
            (
                "pyproject.toml with a pytest table",
                {"pyproject.toml": PYTEST_TABLE},
                CommandGuess(configurations=("Python",), acceptance=("python3 -m pytest",), setup=()),
            ),
            (
                "setup.py and pytest.ini",
                {"setup.py": "", "pytest.ini": ""},
                CommandGuess(configurations=("Python",), acceptance=("python3 -m pytest",), setup=()),
            ),
            (
                "requirements.txt and conftest.py",
                {"requirements.txt": "", "conftest.py": ""},
                CommandGuess(configurations=("Python",), acceptance=("python3 -m pytest",), setup=()),
            ),
            (
                "a test module under tests",
                {"tests/unit/test_app.py": ""},
                CommandGuess(configurations=("Python",), acceptance=("python3 -m unittest",), setup=()),
            ),
            (
                "uv.lock",
                {"pyproject.toml": NO_PYTEST_TABLE, "uv.lock": ""},
                CommandGuess(
                    configurations=("Python",), acceptance=("python3 -m unittest",), setup=("uv sync --frozen",)
                ),
            ),
        ]
        for case, files, expected in rows:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                # Arrange
                create_files(Path(root), files)

                # Act
                guess = guess_commands(Path(root))

                # Assert
                self.assertEqual(guess, expected)

    def test_should_guess_the_commands_of_a_rust_project(self):
        rows = [
            ("with a Cargo.lock", {"Cargo.toml": "", "Cargo.lock": ""}, ("cargo fetch --locked",)),
            ("without a Cargo.lock", {"Cargo.toml": ""}, ()),
        ]
        for case, files, setup in rows:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                # Arrange
                create_files(Path(root), files)

                # Act
                guess = guess_commands(Path(root))

                # Assert
                self.assertEqual(guess, CommandGuess(configurations=("Rust",), acceptance=("cargo test",), setup=setup))

    def test_should_add_the_lines_of_several_configurations_in_their_order(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        create_files(
            Path(root.name), {"Cargo.toml": "", "pyproject.toml": NO_PYTEST_TABLE, "package.json": TEST_SCRIPT}
        )

        # Act
        guess = guess_commands(Path(root.name))

        # Assert
        self.assertEqual(
            guess,
            CommandGuess(
                configurations=("package.json", "Python", "Rust"),
                acceptance=("npm run test", "python3 -m unittest", "cargo test"),
                setup=("npm install",),
            ),
        )

    def test_should_guess_nothing_without_a_supported_configuration(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        create_files(Path(root.name), {"Makefile": "", "docs/test_plan.py": ""})

        # Act
        guess = guess_commands(Path(root.name))

        # Assert
        self.assertEqual(guess, CommandGuess(configurations=(), acceptance=(), setup=()))
