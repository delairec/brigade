import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.convert_study import Study
from brigade.studies.study_run_context import StudyEquipment, StudyRunContext
from brigade.studies.write_answer import write_answer
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
RENDERED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n'
JUDGED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tVERDICT "two oaks"\n'


def create_study(output: str) -> Study:
    return Study(
        name="trees",
        project="oak",
        question=None,
        collectors=(),
        slot="none",
        every=None,
        output=output,
        answer_type="FINDING",
        status="active",
    )


class DocumentDouble:
    def render_document(self, request: dict, runtime) -> dict:
        return {"entities": [{"type": "FINDING", "name": "trees_1", "fields": []}]}


class ForgeDouble:
    def open_issue(self, request: dict, runtime) -> dict:
        return {"url": "https://github.com/acme/oak/issues/3"}


def refuse_collector(name: str, project: Path):
    raise AssertionError(f"the output resolved the collector {name}")


def refuse_launch(request, runtime):
    raise AssertionError("the output launched a run")


class WriteAnswerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes, executable_search_path=str(self.bin))
        self.config_root = self.runtime.paths.config_root
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)
        (self.run_directory / "steps" / "collect.json").write_text('{"collected": []}', encoding="utf-8")

    def create_context(self, output: str) -> StudyRunContext:
        equipment = StudyEquipment(
            collector_equipment=CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github"),
            resolve_collector=refuse_collector,
            document=DocumentDouble(),
            resolve_forge=lambda name: ForgeDouble(),
            launch_run=refuse_launch,
        )
        return StudyRunContext(
            runtime=self.runtime,
            study=create_study(output),
            run_id=RUN_ID,
            run_directory=self.run_directory,
            equipment=equipment,
        )

    def test_should_append_the_answer_brigade_rendered_to_the_entities_of_its_type(self):
        # Arrange
        (self.config_root / "findings.awawa").write_text("FINDING ash_1\n", encoding="utf-8")
        self.processes.answer_corpus_change(
            self.config_root, ("findings.awawa",), "brigade study run: the answer of @STUDY.trees"
        )

        # Act
        written = write_answer(self.create_context("entity:FINDING"))

        # Assert
        self.assertEqual(
            (written, (self.config_root / "findings.awawa").read_text(encoding="utf-8")),
            (
                {"output": "entity:FINDING", "answer": str(self.run_directory / "answer.awawa")},
                f"FINDING ash_1\n\n{RENDERED}",
            ),
        )

    def test_should_keep_the_answer_brigade_rendered_in_the_run(self):
        # Arrange
        self.processes.answer_corpus_change(
            self.config_root, ("findings.awawa",), "brigade study run: the answer of @STUDY.trees"
        )

        # Act
        write_answer(self.create_context("entity:FINDING"))

        # Assert
        self.assertEqual((self.run_directory / "answer.awawa").read_text(encoding="utf-8"), RENDERED)

    def test_should_write_the_answer_the_judging_run_gave(self):
        # Arrange
        (self.run_directory / "answer.awawa").write_text(JUDGED, encoding="utf-8")
        self.processes.answer_corpus_change(
            self.config_root, ("findings.awawa",), "brigade study run: the answer of @STUDY.trees"
        )

        # Act
        write_answer(self.create_context("entity:FINDING"))

        # Assert
        self.assertEqual((self.config_root / "findings.awawa").read_text(encoding="utf-8"), JUDGED)

    def test_should_publish_the_answer_as_an_issue(self):
        # Arrange
        self.processes.answer_entities(
            self.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("FORGE", "github"))}
        )

        # Act
        written = write_answer(self.create_context("issue"))

        # Assert
        self.assertEqual(
            written,
            {
                "output": "issue",
                "answer": str(self.run_directory / "answer.awawa"),
                "issue": "https://github.com/acme/oak/issues/3",
            },
        )

    def test_should_hand_the_answer_to_an_output_executable(self):
        # Arrange
        executable = self.bin / "brigade-output-slack"
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        executable.chmod(0o755)
        self.processes.answer((str(executable),))

        # Act
        written = write_answer(self.create_context("slack"))

        # Assert
        self.assertEqual(written["executable"], str(executable))

    def test_should_write_the_answer_to_a_file_of_the_project(self):
        # Arrange
        checkout = self.run_directory / "checkout"
        branch = f"brigade/study-trees-{RUN_ID}"
        self.processes.answer_entities(self.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("FORGE", "none"))})
        self.processes.answer(
            ("git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"), "origin/main\n"
        )
        self.processes.answer(("git", "worktree", "add", "--quiet", "--detach", str(checkout), "main"))
        self.processes.answer(("git", "switch", "--quiet", "--force-create", branch))
        self.processes.answer(("git", "add", "--", "answer.md"))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", "answer.md"))
        self.processes.answer(("git", "worktree", "remove", "--force", str(checkout)))

        # Act
        written = write_answer(self.create_context("file:answer.md"))

        # Assert
        self.assertEqual(written["branch"], branch)
