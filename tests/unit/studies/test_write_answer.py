import tempfile
import unittest
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.wave_started import WaveStarted
from brigade.studies.convert_study import Study
from brigade.studies.study_run_context import StudyRunContext
from brigade.studies.write_answer import write_answer
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
RENDERED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n'
JUDGED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tVERDICT "two oaks"\n'
REPORTED = 'REPORT oak_w2\n\tWAVE "oak_w2"\n'
WAVE_REPORT = Study(
    name="wave-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    wave="oak_w2",
)
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


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


def create_forge() -> ForgeDouble:
    return ForgeDouble({"open_issue": lambda request: {"url": "https://github.com/acme/oak/issues/3"}})


class WriteAnswerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(
            create_test_paths(self.root, executable_search_path=str(self.bin)), run_process=self.processes
        )
        self.config_root = self.runtime.paths.config_root
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)
        (self.run_directory / "steps" / "collect.json").write_text('{"collected": []}', encoding="utf-8")

    def create_context(self, output: str, study: Study | None = None) -> StudyRunContext:
        equipment = create_study_equipment(
            document=DocumentDouble(), resolve_forge={"github": create_forge()}.__getitem__
        )
        return StudyRunContext(
            runtime=self.runtime,
            study=study or create_study(output),
            run_id=RUN_ID,
            run_directory=self.run_directory,
            equipment=equipment,
        )

    def script_entity_output(self) -> None:
        self.processes.answer_corpus_change(
            self.config_root, ("findings.awawa",), "brigade study run: the answer of @STUDY.trees"
        )

    def test_should_answer_where_the_answer_went(self):
        # Arrange
        self.script_entity_output()

        # Act
        written = write_answer(self.create_context("entity:FINDING"))

        # Assert
        self.assertEqual(written, {"output": "entity:FINDING", "answer": str(self.run_directory / "answer.awawa")})

    def test_should_append_the_answer_brigade_rendered_to_the_entities_of_its_type(self):
        # Arrange
        (self.config_root / "findings.awawa").write_text("FINDING ash_1\n", encoding="utf-8")
        self.script_entity_output()

        # Act
        write_answer(self.create_context("entity:FINDING"))

        # Assert
        self.assertEqual(
            (self.config_root / "findings.awawa").read_text(encoding="utf-8"),
            'FINDING ash_1\n\nFINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n',
        )

    def test_should_keep_the_answer_brigade_rendered_in_the_run(self):
        # Arrange
        self.script_entity_output()

        # Act
        write_answer(self.create_context("entity:FINDING"))

        # Assert
        self.assertEqual((self.run_directory / "answer.awawa").read_text(encoding="utf-8"), RENDERED)

    def test_should_write_the_answer_the_judging_run_gave(self):
        # Arrange
        (self.run_directory / "answer.awawa").write_text(JUDGED, encoding="utf-8")
        self.script_entity_output()

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

    def test_should_publish_the_report_of_a_wave_on_its_integration_branch_once_its_entity_is_written(self):
        # Arrange
        checkout = self.run_directory / "checkout"
        (self.run_directory / "answer.awawa").write_text(REPORTED, encoding="utf-8")
        append_event(
            self.runtime.paths,
            self.runtime.now,
            WaveStarted(wave="oak_w2", project="oak", branch="integration/oak_w2", tasks=("B17",)),
        )
        self.processes.answer_corpus_change(
            self.config_root, ("reports.awawa",), "brigade study run: the answer of @STUDY.wave-report"
        )
        self.processes.answer_entities(
            self.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("FORGE", "none"), ("CORPUS", "corpus"))}
        )
        self.processes.answer(("git", "fetch", "--quiet", "origin", "integration/oak_w2"))
        self.processes.answer(
            ("git", "worktree", "add", "--quiet", "--detach", str(checkout), "origin/integration/oak_w2")
        )
        self.processes.answer(("git", "switch", "--quiet", "--force-create", "integration/oak_w2"))
        self.processes.answer(("git", "add", "--", "corpus/waves/2-report.md"))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", "corpus/waves/2-report.md"))
        self.processes.answer(("git", "push", "--quiet", "origin", "integration/oak_w2"))
        self.processes.answer(("git", "worktree", "remove", "--force", str(checkout)))

        # Act
        written = write_answer(self.create_context("entity:REPORT", WAVE_REPORT))

        # Assert
        self.assertEqual(
            written,
            {
                "output": "entity:REPORT",
                "answer": str(self.run_directory / "answer.awawa"),
                "report": "corpus/waves/2-report.md",
                "branch": "integration/oak_w2",
                "pull_request": None,
            },
        )
