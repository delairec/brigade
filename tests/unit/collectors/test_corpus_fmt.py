from brigade.collectors.corpus_fmt import collect
from tests.unit.collectors.scan_fixtures import ENVIRONMENT_OF_OAK, ScanCollectorTestCase, create_equipment

FORMAT_CHECK = ("awawa", "fmt", "--check", ".")


class CorpusFmtCollectorTest(ScanCollectorTestCase):
    def test_should_print_one_item_per_file_the_format_would_rewrite_at_the_main_branch(self):
        # Arrange
        self.register_oak(("CORPUS", "corpus"))
        self.create_cached_tree_of_main()
        self.processes.answer(
            FORMAT_CHECK,
            exit_code=1,
            stderr="would reformat ./corpus/tasks.awawa\nwould reformat ./corpus/decisions.awawa\n",
        )

        # Act
        document = collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(None))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "corpus-fmt",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"files": 2},
                "items": [
                    {"file": "corpus/tasks.awawa", "fingerprint": "corpus/tasks.awawa"},
                    {"file": "corpus/decisions.awawa", "fingerprint": "corpus/decisions.awawa"},
                ],
            },
        )

    def test_should_leave_out_what_the_format_prints_beside_the_files_it_would_rewrite(self):
        # Arrange
        self.register_oak(("CORPUS", "corpus"))
        self.create_cached_tree_of_main()
        self.processes.answer(
            FORMAT_CHECK,
            exit_code=1,
            stderr="./corpus/broken.awawa:3:1: unterminated string\nwould reformat ./corpus/tasks.awawa\n",
        )

        # Act
        document = collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(None))

        # Assert
        self.assertEqual(document["items"], [{"file": "corpus/tasks.awawa", "fingerprint": "corpus/tasks.awawa"}])

    def test_should_check_the_checkout_of_the_main_branch_and_change_nothing(self):
        # Arrange
        self.register_oak(("CORPUS", "corpus"))
        tree = self.create_cached_tree_of_main()
        self.processes.answer(FORMAT_CHECK)

        # Act
        collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(None))

        # Assert
        self.assertEqual(
            [(request.argv, request.cwd) for request in self.processes.requests][-2:],
            [
                (("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "main^{commit}"), "/srv/oak"),
                (FORMAT_CHECK, str(tree)),
            ],
        )
