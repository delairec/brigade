import shutil
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_archive():
    distribution = ROOT / "dist"
    distribution.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as staging:
        shutil.copytree(
            ROOT / "brigade",
            Path(staging) / "brigade",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        zipapp.create_archive(
            staging,
            target=distribution / "brigade.pyz",
            interpreter="/usr/bin/env python3",
            main="brigade.launcher:launch",
            compressed=True,
        )


build_archive()
