import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

PACKAGE_SCRIPTS = ("test", "lint", "typecheck")
PACKAGE_MANAGERS = (
    (("bun.lock", "bun.lockb"), "bun"),
    (("pnpm-lock.yaml",), "pnpm"),
    (("yarn.lock",), "yarn"),
)
NPM = "npm"
PYTHON_MARKERS = ("pyproject.toml", "setup.py", "requirements.txt")
PYTEST_MARKERS = ("pytest.ini", "conftest.py")


@dataclass(frozen=True)
class CommandGuess:
    configurations: tuple[str, ...]
    acceptance: tuple[str, ...]
    setup: tuple[str, ...]


NO_GUESS = CommandGuess(configurations=(), acceptance=(), setup=())


def _read_scripts(package_json: Path) -> dict:
    try:
        scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
    except (ValueError, AttributeError):
        return {}
    return scripts if isinstance(scripts, dict) else {}


def _choose_package_manager(root: Path) -> str:
    for lockfiles, manager in PACKAGE_MANAGERS:
        if any((root / lockfile).exists() for lockfile in lockfiles):
            return manager
    return NPM


def _choose_package_setup(root: Path, manager: str) -> str:
    if manager != NPM:
        return f"{manager} install --frozen-lockfile"
    if (root / "package-lock.json").exists():
        return "npm ci"
    return "npm install"


def _guess_package_json(root: Path) -> CommandGuess:
    if not (root / "package.json").is_file():
        return NO_GUESS
    scripts = _read_scripts(root / "package.json")
    manager = _choose_package_manager(root)
    return CommandGuess(
        configurations=("package.json",),
        acceptance=tuple(f"{manager} run {script}" for script in PACKAGE_SCRIPTS if script in scripts),
        setup=(_choose_package_setup(root, manager),),
    )


def _has_pytest_table(pyproject: Path) -> bool:
    try:
        configuration = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return "ini_options" in configuration.get("tool", {}).get("pytest", {})


def _detect_python(root: Path) -> bool:
    if any((root / marker).is_file() for marker in PYTHON_MARKERS):
        return True
    tests = root / "tests"
    return tests.is_dir() and any(tests.rglob("test_*.py"))


def _guess_python(root: Path) -> CommandGuess:
    if not _detect_python(root):
        return NO_GUESS
    pytest_marked = any((root / marker).is_file() for marker in PYTEST_MARKERS)
    uses_pytest = pytest_marked or _has_pytest_table(root / "pyproject.toml")
    return CommandGuess(
        configurations=("Python",),
        acceptance=("python3 -m pytest" if uses_pytest else "python3 -m unittest",),
        setup=("uv sync --frozen",) if (root / "uv.lock").exists() else (),
    )


def _guess_rust(root: Path) -> CommandGuess:
    if not (root / "Cargo.toml").is_file():
        return NO_GUESS
    return CommandGuess(
        configurations=("Rust",),
        acceptance=("cargo test",),
        setup=("cargo fetch --locked",) if (root / "Cargo.lock").exists() else (),
    )


def guess_commands(root: Path) -> CommandGuess:
    guesses = (_guess_package_json(root), _guess_python(root), _guess_rust(root))
    return CommandGuess(
        configurations=tuple(item for guess in guesses for item in guess.configurations),
        acceptance=tuple(item for guess in guesses for item in guess.acceptance),
        setup=tuple(item for guess in guesses for item in guess.setup),
    )
