import os
import tempfile
import unittest
from pathlib import Path

from brigade.corpus.corpus_view_answerer import CorpusViewAnswerer
from brigade.corpus.read_entities import Entity, EntityField
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.corpus.awawa_corpus_double import (
    STRING,
    FakeCorpus,
    FakeEntity,
    create_awawa_double,
    declare_field,
    declare_literals,
    declare_reference,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

PROJECTS = (Entity(name="app", fields=(EntityField(name="PATH", value="/srv/app"), EntityField("MAIN", "main"))),)
ANSWERED_CORPUS = FakeCorpus(
    entities=(
        FakeEntity("TASK", "B1", "implemented", (("TITLE", ('"Read the corpus"',)),)),
        FakeEntity("TASK", "B2", "todo", (("TITLE", ('"Draw the board"',)), ("AFTER", ("@TASK.B1",))), line=8),
    ),
    schemas={
        "TASK": [
            declare_field("TITLE", STRING, required=True),
            declare_field("STATUS", *declare_literals("todo", "implemented"), required=True),
            declare_field("AFTER", declare_reference("TASK"), repeatable=True),
        ]
    },
)
BOARD_MESSAGE = {"project": "app", "ref": "worktree:b42", "view": "board", "type": "TASK", "filter": ["STATUS=todo"]}
LATER_MTIME_NS = 2_000_000_000_000_000_000


def list_worktrees(worktree: Path, head: str) -> ProcessAnswer:
    return ProcessAnswer(
        stdout=(
            "worktree /srv/app\0HEAD 8885daa\0branch refs/heads/main\0\0"
            f"worktree {worktree}\0HEAD {head}\0branch refs/heads/b42\0\0"
        )
    )


class CorpusViewAnswererTestCase(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.worktree = Path(root.name) / "app-b42"
        self.corpus_file = self.worktree / "corpus" / "tasks.awawa"
        self.corpus_file.parent.mkdir(parents=True)
        self.corpus_file.write_text('TASK B1\n\tTITLE "Read the corpus"\n')
        self.git = ScriptedProcessRunner(
            {
                ("git", "worktree", "list"): list_worktrees(self.worktree, "de446f3"),
                ("awawa-web", "--help"): ProcessAnswer(),
            }
        )
        self.awawa = ScriptedProcessRunner({}, fallback=create_awawa_double(ANSWERED_CORPUS, self.worktree))
        runtime = create_test_runtime(create_test_paths(Path(root.name) / "machine"), run_process=self.git.run)
        self.answerer = CorpusViewAnswerer(PROJECTS, runtime, self.awawa.run)


class CorpusViewAnswererTest(CorpusViewAnswererTestCase):
    def test_should_answer_the_document_of_the_view_of_the_tree_read(self):
        # Act
        answer = self.answerer.answer(BOARD_MESSAGE)

        # Assert
        document = answer["document"]
        self.assertEqual(document["view"], "board")
        self.assertEqual(document["sha"], "de446f3")
        self.assertEqual(document["types"], ["TASK"])
        self.assertEqual(document["awawa_web"], "http://127.0.0.1:7878/")
        self.assertEqual(document["columns"][0]["entities"][0]["code"], "B2")

    def test_should_answer_an_error_the_corpus_command_would_refuse(self):
        # Arrange
        message = {"project": "shop", "view": "board", "type": "TASK"}

        # Act
        answer = self.answerer.answer(message)

        # Assert
        self.assertEqual(answer, {"error": "@PROJECT.shop is not registered"})


class CorpusViewAnswererOfAnUnchangedCorpusTest(CorpusViewAnswererTestCase):
    def test_should_run_the_awawa_binary_no_more_at_a_second_request(self):
        # Arrange
        rows = [
            ("tree", {"project": "app", "ref": "worktree:b42", "view": "tree", "entity": "@TASK.B2"}),
            ("board", BOARD_MESSAGE),
            ("dependencies", {"project": "app", "ref": "worktree:b42", "view": "dependencies", "type": "TASK"}),
            ("health", {"project": "app", "ref": "worktree:b42", "view": "health", "search": "board"}),
        ]
        for view, message in rows:
            with self.subTest(view=view):
                # Arrange
                self.answerer.answer(message)
                self.awawa.argvs.clear()

                # Act
                answer = self.answerer.answer(message)

                # Assert
                self.assertEqual(answer["document"]["view"], view)
                self.assertEqual(self.awawa.argvs, [])


class CorpusViewAnswererOfAChangedCorpusTest(CorpusViewAnswererTestCase):
    def test_should_read_the_corpus_again_once_an_awawa_file_changed(self):
        # Arrange
        self.answerer.answer(BOARD_MESSAGE)
        self.awawa.argvs.clear()
        self.corpus_file.write_text('TASK B1\n\tTITLE "Read the corpus again"\n')
        os.utime(self.corpus_file, ns=(LATER_MTIME_NS, LATER_MTIME_NS))

        # Act
        self.answerer.answer(BOARD_MESSAGE)

        # Assert
        self.assertIn(("awawa", "status", "--json", str(self.worktree)), self.awawa.argvs)

    def test_should_read_the_corpus_again_once_the_ref_names_another_commit(self):
        # Arrange
        self.answerer.answer(BOARD_MESSAGE)
        self.awawa.argvs.clear()
        self.git.answers[("git", "worktree", "list")] = list_worktrees(self.worktree, "0be1f00")

        # Act
        answer = self.answerer.answer(BOARD_MESSAGE)

        # Assert
        self.assertEqual(answer["document"]["sha"], "0be1f00")
        self.assertIn(("awawa", "status", "--json", str(self.worktree)), self.awawa.argvs)
