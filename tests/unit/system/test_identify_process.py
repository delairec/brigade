import unittest
from pathlib import Path

from brigade.system.identify_process import identify_process

PID = 4242
STAT = "4242 (python3 (worker)) S 1 4242 4242 0 -1 4194560 0 0 0 0 0 0 0 0 20 0 1 0 987654 0 0\n"
BOOT_ID = "7c1a8f2e-6c3f-4b37-9b1d-5655b8e0a11d\n"


class KernelFilesDouble:
    def __init__(self, contents: dict[Path, str | Exception]):
        self.contents = contents

    def read(self, path: Path) -> str:
        content = self.contents[path]
        if isinstance(content, Exception):
            raise content
        return content


class IdentifyProcessTest(unittest.TestCase):
    def test_should_identify_a_process_by_its_start_time_and_the_boot_of_the_kernel(self):
        # Arrange
        kernel_files = KernelFilesDouble(
            {Path("/proc/4242/stat"): STAT, Path("/proc/sys/kernel/random/boot_id"): BOOT_ID}
        )

        # Act
        identity = identify_process(PID, kernel_files.read)

        # Assert
        self.assertEqual(identity, "987654 7c1a8f2e-6c3f-4b37-9b1d-5655b8e0a11d")

    def test_should_identify_no_process_whose_stat_is_gone_or_released_while_read(self):
        for case, failure in [
            ("gone", FileNotFoundError(2, "No such file or directory")),
            ("released while read", ProcessLookupError(3, "No such process")),
        ]:
            with self.subTest(case=case):
                # Arrange
                kernel_files = KernelFilesDouble({Path("/proc/4242/stat"): failure})

                # Act
                identity = identify_process(PID, kernel_files.read)

                # Assert
                self.assertIsNone(identity)
