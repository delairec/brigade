import subprocess


class ProcessLauncher:
    @staticmethod
    def run(argv: list, *, check: bool, **options) -> subprocess.CompletedProcess:
        return subprocess.run(argv, check=check, **options)  # noqa: S603 - the argv of a test, which its caller writes

    @staticmethod
    def start(argv: list, **options) -> subprocess.Popen:
        return subprocess.Popen(argv, **options)  # noqa: S603 - the argv of a test, which its caller writes
