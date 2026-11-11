import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.cli.forgeless_wave_rehearser import ForgelessWaveRehearser
from tests.cli.temporary_machine import REPOSITORY_ROOT, TemporaryMachine
from tests.cli.test_collect import install_executable
from tests.cli.wave_rehearser import ClassCleanupRegistrar
from tests.process_launcher import ProcessLauncher

COMMENTED_CLIENT_LINE = '# client = ""\n'
COMMENTED_FAKE_TABLE = '# [clients.fake]\n# recordings = ""\n'


def build_archive(clone_root: Path) -> Path:
    shutil.copytree(REPOSITORY_ROOT / "brigade", clone_root / "brigade", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(REPOSITORY_ROOT / "build.py", clone_root / "build.py")
    ProcessLauncher.run([sys.executable, "build.py"], cwd=clone_root, check=True, stdout=subprocess.DEVNULL)
    return clone_root / "dist" / "brigade.pyz"


class FreshAccountWaveRehearser(ForgelessWaveRehearser):
    def __init__(self, registrar: ClassCleanupRegistrar):
        self.registrar = registrar
        self.root = tempfile.TemporaryDirectory()
        registrar.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.archive = build_archive(root / "clone")
        self.machine = TemporaryMachine(root)
        self.move_the_git_identity_out_of_home()
        self.state = self.machine.state_home / "brigade"
        self.store = root / "forge"
        self.remote = self.store / "remote.git"
        self.tools = root / "tools"
        self.machine.install_awawa(registrar)
        self.reduce_the_search_path()
        self.install_tools()
        self.init = self.run_brigade("init")
        self.machine.pause_the_built_in_studies_of_shop()
        self.prepare_sandbox(root / "projects" / "shop")
        self.prepare_client(root / "recordings", root / "plays")
        self.doctor_before_the_project = self.run_brigade("doctor", "--json")
        self.register_sandbox()
        self.doctor_after_the_project = self.run_brigade("doctor", "--json")

    def move_the_git_identity_out_of_home(self) -> None:
        git_directory = self.machine.config_home / "git"
        git_directory.mkdir(parents=True)
        (self.machine.home / ".gitconfig").rename(git_directory / "config")

    def reduce_the_search_path(self) -> None:
        awawa = Path(shutil.which("awawa", path=self.machine.search_path))
        git = Path(shutil.which("git", path=self.machine.search_path))
        directories = (str(awawa.parent), str(Path(sys.executable).parent), str(git.parent))
        self.machine.search_path = os.pathsep.join(directories)

    def install_tools(self) -> None:
        install_executable(self.tools / "brigade", f'#!/bin/sh\nexec "{sys.executable}" "{self.archive}" "$@"\n')

    def prepare_client(self, recordings: Path, plays: Path) -> None:
        configuration = self.machine.corpus / "config.toml"
        written_by_init = configuration.read_text()
        super().prepare_client(recordings, plays)
        configured = written_by_init.replace(COMMENTED_CLIENT_LINE, 'client = "fake"\n').replace(
            COMMENTED_FAKE_TABLE, f'[clients.fake]\nrecordings = "{recordings}"\nplays = "{plays}"\n'
        )
        configuration.write_text(configured)

    def run_brigade(self, *arguments: str):
        return self.machine.run_brigade(self.archive, *arguments, environment=self.describe_environment())
