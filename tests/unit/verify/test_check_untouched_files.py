import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.git.count_changed_lines import ChangedFile
from brigade.verify.check_untouched_files import UntouchedFilesFacts, check_untouched_files
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class CheckUntouchedFilesTest(unittest.TestCase):
    def test_should_fail_a_corpus_file_that_changes_while_none_of_its_entities_does(self):
        # Arrange
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        base_tree, head_tree = root / "base", root / "head"
        moved = {
            "added": [{"file": "corpus/tasks.awawa"}],
            "changed": [{"file": "./corpus/decisions.awawa"}],
            "removed": [{"file": "corpus/old.awawa"}],
        }
        awawa = RecordingProcessRunner(
            {
                ("awawa", "diff", str(base_tree), str(head_tree), "--json"): ProcessAnswer(stdout=json.dumps(moved)),
            }
        )
        changed = (
            ChangedFile(path="corpus/tasks.awawa", insertions=4, deletions=0),
            ChangedFile(path="corpus/decisions.awawa", insertions=1, deletions=1),
            ChangedFile(path="corpus/old.awawa", insertions=0, deletions=9),
            ChangedFile(path="corpus/rules.awawa", insertions=2, deletions=2),
            ChangedFile(path="brigade/cli.py", insertions=3, deletions=1),
        )

        # Act
        check = check_untouched_files(
            awawa, UntouchedFilesFacts(base_tree=base_tree, head_tree=head_tree, changed=changed)
        )

        # Assert
        self.assertEqual(
            check,
            {
                "name": "untouched_files",
                "verdict": "fail",
                "findings": ["corpus/rules.awawa changes while none of its entities does"],
            },
        )
