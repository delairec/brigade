import os
import shutil
import tempfile
import zipapp

ROOT = os.path.dirname(os.path.abspath(__file__))


def build_archive():
    distribution = os.path.join(ROOT, "dist")
    os.makedirs(distribution, exist_ok=True)
    with tempfile.TemporaryDirectory() as staging:
        shutil.copytree(
            os.path.join(ROOT, "brigade"),
            os.path.join(staging, "brigade"),
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        zipapp.create_archive(
            staging,
            target=os.path.join(distribution, "brigade.pyz"),
            interpreter="/usr/bin/env python3",
            main="brigade.launcher:launch",
            compressed=True,
        )


build_archive()
