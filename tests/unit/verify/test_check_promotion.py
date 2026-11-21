import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import CommandFailed
from brigade.verify.check_promotion import PromotionFacts, check_promotion
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

NO_CHANGED_FILE = ()


def create_spec(text: str, anchor: str) -> dict:
    return {
        "name": "SPEC",
        "atoms": [json.dumps(text)],
        "fields": [{"name": "IMPL", "atoms": [json.dumps(anchor)], "fields": []}],
    }


class CheckPromotionTest(unittest.TestCase):
    def setUp(self):
        self.head_tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.head_tree)
        (self.head_tree / "brigade").mkdir()
        (self.head_tree / "brigade" / "cli.py").write_text("def main(arguments):\n")

    def check(self, fields: list[dict]) -> dict:
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", str(self.head_tree)): ProcessAnswer(
                    stdout=json.dumps({"fields": fields})
                )
            }
        )
        return check_promotion(
            awawa,
            PromotionFacts(
                head_tree=self.head_tree, repository_tree=self.head_tree, task="B1", pr=160, changed=NO_CHANGED_FILE
            ),
        )

    def test_should_pass_a_task_implemented_delivered_by_the_pull_request_and_anchored(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ['"160"'], "fields": []},
                create_spec("runs the command line", "brigade/cli.py::def main"),
            ]
        )

        # Assert
        self.assertEqual(check, {"name": "promotion", "result": "ok", "findings": []})

    def test_should_fail_a_task_left_unpromoted_and_unanchored(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["todo"], "fields": []},
                create_spec("runs the command line", "brigade/cli.py::def launch"),
                create_spec("ships a launcher", "brigade/launcher.py::def launch"),
            ]
        )

        # Assert
        self.assertEqual(
            check,
            {
                "name": "promotion",
                "result": "fail",
                "findings": [
                    "@TASK.B1 is STATUS todo, not implemented",
                    "@TASK.B1 is delivered by no pull request, not by #160",
                    "SPEC 1 has no IMPL whose anchor resolves: runs the command line",
                    "SPEC 2 has no IMPL whose anchor resolves: ships a launcher",
                ],
            },
        )

    def test_should_fail_a_task_delivered_by_another_pull_request(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ["158"], "fields": []},
            ]
        )

        # Assert
        self.assertEqual(check["findings"], ["@TASK.B1 is delivered by #158, not by #160"])

    def test_should_name_an_unanchored_criterion_with_the_backslash_awawa_keeps(self):
        # Act
        check = self.check(
            [
                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                {"name": "DELIVERED_BY", "atoms": ["160"], "fields": []},
                {"name": "SPEC", "atoms": [r'"matches brigade/cli\.py"'], "fields": []},
            ]
        )

        # Assert
        self.assertEqual(
            check,
            {
                "name": "promotion",
                "result": "fail",
                "findings": [r"SPEC 1 has no IMPL whose anchor resolves: matches brigade/cli\.py"],
            },
        )

    def test_should_pass_a_task_implemented_and_anchored_without_a_pull_request_to_deliver_it(self):
        # Arrange
        no_pull_request = None
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", str(self.head_tree)): ProcessAnswer(
                    stdout=json.dumps(
                        {
                            "fields": [
                                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                                create_spec("runs the command line", "brigade/cli.py::def main"),
                            ]
                        }
                    )
                )
            }
        )
        facts = PromotionFacts(
            head_tree=self.head_tree,
            repository_tree=self.head_tree,
            task="B1",
            pr=no_pull_request,
            changed=NO_CHANGED_FILE,
        )

        # Act
        check = check_promotion(awawa, facts)

        # Assert
        self.assertEqual(check, {"name": "promotion", "result": "ok", "findings": []})


class CheckPromotionOfAHeadWithoutTheTaskTest(unittest.TestCase):
    def test_should_fail_on_a_task_the_head_does_not_define(self):
        # Arrange
        head_tree = Path("/srv/shop-head")
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", str(head_tree)): ProcessAnswer(
                    exit_code=1, stderr="awawa show: @TASK.B1 is not defined in the workspace\n"
                )
            }
        )

        # Act
        check = check_promotion(
            awawa,
            PromotionFacts(head_tree=head_tree, repository_tree=head_tree, task="B1", pr=160, changed=NO_CHANGED_FILE),
        )

        # Assert
        self.assertEqual(
            check, {"name": "promotion", "result": "fail", "findings": ["@TASK.B1 is not defined at the head"]}
        )


class CheckPromotionOfAnAreaTest(unittest.TestCase):
    def setUp(self):
        self.repository_tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repository_tree)
        self.area_tree = self.repository_tree / "brigade"
        self.area_tree.mkdir()
        (self.repository_tree / "src").mkdir()
        (self.repository_tree / "src" / "cart.py").write_text("def add_item():\n")
        (self.area_tree / "notes.py").write_text("def only_in_the_area():\n")

    def check(self, anchor: str) -> dict:
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", str(self.area_tree)): ProcessAnswer(
                    stdout=json.dumps(
                        {
                            "fields": [
                                {"name": "STATUS", "atoms": ["implemented"], "fields": []},
                                create_spec("adds an item", anchor),
                            ]
                        }
                    )
                )
            }
        )
        no_pull_request = None
        facts = PromotionFacts(
            head_tree=self.area_tree,
            repository_tree=self.repository_tree,
            task="B1",
            pr=no_pull_request,
            changed=NO_CHANGED_FILE,
        )
        return check_promotion(awawa, facts)

    def test_should_pass_a_task_anchored_on_a_file_outside_the_area(self):
        # Act
        check = self.check("src/cart.py::def add_item")

        # Assert
        self.assertEqual(check, {"name": "promotion", "result": "ok", "findings": []})

    def test_should_refuse_an_anchor_read_from_the_area_instead_of_the_repository(self):
        # Act
        check = self.check("notes.py::def only_in_the_area")

        # Assert
        self.assertEqual(check["findings"], ["SPEC 1 has no IMPL whose anchor resolves: adds an item"])

    def test_should_refuse_a_file_absent_from_the_repository(self):
        # Act
        check = self.check("src/absent.py::def add_item")

        # Assert
        self.assertEqual(check["findings"], ["SPEC 1 has no IMPL whose anchor resolves: adds an item"])

    def test_should_refuse_a_text_absent_from_the_file(self):
        # Act
        check = self.check("src/cart.py::def remove_item")

        # Assert
        self.assertEqual(check["findings"], ["SPEC 1 has no IMPL whose anchor resolves: adds an item"])

    def test_should_refuse_an_anchor_leaving_the_repository(self):
        # Arrange
        outside = self.repository_tree.parent / f"{self.repository_tree.name}-outside.py"
        outside.write_text("def add_item():\n")
        self.addCleanup(outside.unlink)
        (self.repository_tree / "src" / "link.py").symlink_to(outside)
        for case, anchor in [
            ("an absolute path", f"{outside}::def add_item"),
            ("an absolute path with no text", str(outside)),
            ("a path climbing out of the repository", f"../{outside.name}::def add_item"),
            ("a symbolic link to a file outside", "src/link.py::def add_item"),
        ]:
            with self.subTest(case=case):
                # Act
                check = self.check(anchor)

                # Assert
                self.assertEqual(check["findings"], ["SPEC 1 has no IMPL whose anchor resolves: adds an item"])

    def test_should_pass_a_symbolic_link_staying_in_the_repository(self):
        # Arrange
        (self.repository_tree / "src" / "alias.py").symlink_to(self.repository_tree / "src" / "cart.py")

        # Act
        check = self.check("src/alias.py::def add_item")

        # Assert
        self.assertEqual(check, {"name": "promotion", "result": "ok", "findings": []})


class CheckPromotionOfAHeadAwawaCannotReadTest(unittest.TestCase):
    def test_should_fail_the_check_rather_than_say_the_task_is_not_defined(self):
        # Arrange
        head_tree = Path("/srv/shop-head")
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", str(head_tree)): ProcessAnswer(
                    exit_code=2, stderr="awawa: corpus/tasks.awawa is not UTF-8\n"
                )
            }
        )
        facts = PromotionFacts(
            head_tree=head_tree, repository_tree=head_tree, task="B1", pr=160, changed=NO_CHANGED_FILE
        )

        # Act
        with self.assertRaises(CommandFailed) as raised:
            check_promotion(awawa, facts)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "awawa show @TASK.B1 --json /srv/shop-head exited 2: awawa: corpus/tasks.awawa is not UTF-8",
        )


IMPLEMENTED_AND_DELIVERED = [
    {"name": "STATUS", "atoms": ["implemented"], "fields": []},
    {"name": "DELIVERED_BY", "atoms": ['"160"'], "fields": []},
]
HARBOUR_COVERS_TIDES = {"name": "COVERS", "atoms": ['"tides"'], "fields": []}


class CheckPromotionOfATaskCitingAReferenceTest(unittest.TestCase):
    def check(self, reference: dict, changed: tuple[str, ...]) -> dict:
        head_tree = Path("/srv/shop-head")
        awawa = RecordingProcessRunner(
            {
                ("awawa", "show", "@TASK.B1", "--json", str(head_tree)): ProcessAnswer(
                    stdout=json.dumps({"fields": [*IMPLEMENTED_AND_DELIVERED, reference]})
                )
            }
        )
        facts = PromotionFacts(head_tree=head_tree, repository_tree=head_tree, task="B1", pr=160, changed=changed)
        return check_promotion(awawa, facts)

    def test_should_fail_a_branch_that_changes_the_reference_its_task_is_judged_against(self):
        # Arrange
        reference = {"name": "REFERENCE", "atoms": ['"artifact/harbour/index.html"'], "fields": [HARBOUR_COVERS_TIDES]}

        # Act
        check = self.check(reference, ("brigade/tides.py", "artifact/harbour/index.html"))

        # Assert
        self.assertEqual(
            check,
            {
                "name": "promotion",
                "result": "fail",
                "findings": [
                    (
                        "artifact/harbour/index.html is the REFERENCE @TASK.B1 is judged against, and its branch changes"
                        " it: a task delivering its reference says so with REVISES"
                    )
                ],
            },
        )

    def test_should_pass_a_branch_that_leaves_the_reference_of_its_task_unchanged(self):
        # Arrange
        reference = {"name": "REFERENCE", "atoms": ['"artifact/harbour/index.html"'], "fields": [HARBOUR_COVERS_TIDES]}

        # Act
        check = self.check(reference, ("brigade/tides.py",))

        # Assert
        self.assertEqual(check, {"name": "promotion", "result": "ok", "findings": []})

    def test_should_pass_a_branch_delivering_the_reference_its_task_says_it_revises(self):
        # Arrange
        revises = {"name": "REVISES", "atoms": ['"the task draws the harbour page itself"'], "fields": []}
        reference = {
            "name": "REFERENCE",
            "atoms": ['"artifact/harbour/index.html"'],
            "fields": [revises, HARBOUR_COVERS_TIDES],
        }

        # Act
        check = self.check(reference, ("artifact/harbour/index.html",))

        # Assert
        self.assertEqual(check, {"name": "promotion", "result": "ok", "findings": []})
