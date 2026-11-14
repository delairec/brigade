import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.convert_study import Study
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.study_run_context import StudyRunContext
from brigade.studies.write_answer import write_answer
from brigade.system.parse_configuration import Configuration
from brigade.waves.locate_branch_worktree import locate_branch_worktree
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.built_in_triage import BUILT_IN_TRIAGE
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
RENDERED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n'
JUDGED = 'FINDING trees_20261019T090000Z_aaaaaa\n\tVERDICT "two oaks"\n'
RATIFIED_PATTERN = 'PATTERN cli_is_hard_to_read\n\tTITLE "the cli is hard to read"\n\tSTATUS ratified\n'
PROPOSED_PATTERN = (
    'PATTERN slow_tick\n\tTITLE "the tick is slow"\n\tSTATUS new\n\tEVIDENCE "note:5f2b1c0d9e8a"\n\tACTION dismiss\n'
)
HELD_PATTERNS = (
    'PATTERN cli_is_hard_to_read\n\tTITLE "the cli is hard to read"\n\tSTATUS ratified\n\tEVIDENCE "rt:9"\n\n'
    'PATTERN tick_is_slow\n\tTITLE "the tick is slow"\n\tSTATUS new\n\tEVIDENCE "rt:10"\n\tACTION wave\n'
)
EVIDENCE_ADDED = 'PATTERN cli_is_hard_to_read\n\tEVIDENCE "rt:101 another thread"\n'
REPORTED = 'REPORT oak_M6\n\tMILESTONE "M6"\n'
MILESTONES_PATH = "corpus/milestones.awawa"
MILESTONE_REPORT = Study(
    name="milestone-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    milestone=MilestoneReportOrder(
        project="oak", milestone="M6", branch="integration/hardening", waves=("oak_w2",), tasks=("B17",)
    ),
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

    def create_context(
        self, output: str, study: Study | None = None, configuration: Configuration | None = None
    ) -> StudyRunContext:
        equipment = create_study_equipment(
            collector_equipment=CollectorEquipment(
                configuration=configuration or Configuration(), forge=None, forge_name="github", resolve_client=None
            ),
            document=DocumentDouble(),
            resolve_forge={"github": create_forge()}.__getitem__,
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

    def test_should_record_the_answer_of_a_study_answering_into_the_inbox(self):
        # Arrange
        judged_study = dataclasses.replace(create_study("inbox"), slot="report")

        # Act
        written = write_answer(self.create_context("inbox", judged_study))

        # Assert
        self.assertEqual(
            written,
            {
                "output": "inbox",
                "answer": str(self.run_directory / "answer.awawa"),
                "signal": "af53cf2028ed09d28bc16549166fcb64657c57afcb0ea5cb90f877e5731c2aec",
                "fingerprint": "study:trees:76c781bcf86d",
            },
        )

    def test_should_record_the_items_of_a_scan_answering_into_the_inbox(self):
        # Arrange
        document = self.root / "collected.json"
        document.write_text(json.dumps({"items": [{"fingerprint": "spike"}]}), encoding="utf-8")
        (self.run_directory / "steps" / "collect.json").write_text(
            json.dumps({"collected": [{"collector": "stale-branches", "summary": {}, "document": str(document)}]}),
            encoding="utf-8",
        )

        # Act
        written = write_answer(self.create_context("inbox"))

        # Assert
        self.assertEqual(written, {"output": "inbox", "answer": str(self.run_directory / "answer.awawa"), "signals": 1})

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

    def test_should_commit_the_patterns_of_the_triage_to_the_operational_corpus(self):
        # Arrange
        (self.config_root / "patterns.awawa").write_text(RATIFIED_PATTERN, encoding="utf-8")
        (self.run_directory / "answer.awawa").write_text(PROPOSED_PATTERN, encoding="utf-8")
        self.processes.answer_corpus_change(
            self.config_root, ("patterns.awawa",), "brigade study run: the answer of @STUDY.triage"
        )

        # Act
        write_answer(self.create_context("entity:PATTERN", BUILT_IN_TRIAGE))

        # Assert
        self.assertEqual(
            (self.config_root / "patterns.awawa").read_text(encoding="utf-8"), f"{RATIFIED_PATTERN}\n{PROPOSED_PATTERN}"
        )
        self.assertIn(
            ("git", "commit", "--quiet", "-m", "brigade study run: the answer of @STUDY.triage"),
            self.processes.list_argvs(),
        )

    def test_should_add_the_evidence_of_the_answer_to_the_held_pattern_and_write_no_new_pattern(self):
        # Arrange
        (self.config_root / "patterns.awawa").write_text(HELD_PATTERNS, encoding="utf-8")
        (self.run_directory / "answer.awawa").write_text(EVIDENCE_ADDED, encoding="utf-8")
        self.processes.answer_corpus_change(
            self.config_root, ("patterns.awawa",), "brigade study run: the answer of @STUDY.triage"
        )

        # Act
        write_answer(self.create_context("entity:PATTERN", BUILT_IN_TRIAGE))

        # Assert
        self.assertEqual(
            (self.config_root / "patterns.awawa").read_text(encoding="utf-8"),
            'PATTERN cli_is_hard_to_read\n\tTITLE "the cli is hard to read"\n\tSTATUS ratified\n\tEVIDENCE "rt:9"\n'
            '\tEVIDENCE "rt:101 another thread"\n\n'
            'PATTERN tick_is_slow\n\tTITLE "the tick is slow"\n\tSTATUS new\n\tEVIDENCE "rt:10"\n\tACTION wave\n',
        )

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

    def test_should_publish_the_report_of_a_milestone_on_its_branch_once_its_entity_is_written(self):
        # Arrange
        worktree_root = str(self.root / "worktrees")
        checkout = locate_branch_worktree(Path("/srv/oak"), worktree_root, "integration/hardening")
        (self.run_directory / "answer.awawa").write_text(REPORTED, encoding="utf-8")
        self.processes.answer_corpus_change(
            self.config_root, ("reports.awawa",), "brigade study run: the answer of @STUDY.milestone-report"
        )
        self.processes.answer_entities(
            self.config_root,
            "PROJECT",
            {"oak": (("PATH", "/srv/oak"), ("FORGE", "none"), ("CORPUS", "corpus"), ("MAIN", "main"))},
        )
        self.processes.answer(("git", "worktree", "list", "--porcelain", "-z"), stdout="")
        self.processes.answer(("git", "worktree", "add", "--quiet", str(checkout), "integration/hardening"))
        self.processes.answer(("git", "reset", "--quiet", "--hard", "integration/hardening"))
        self.processes.answer(("git", "switch", "--quiet", "--force-create", "integration/hardening"))
        self.processes.answer(("git", "add", "--", "corpus/milestones/M6-report.md"))
        self.processes.answer(("git", "diff", "--cached", "--quiet", "--", "corpus/milestones/M6-report.md"))
        self.processes.answer_json(
            ("awawa", "show", "@MILESTONE.M6", "--json", str(checkout)), {"file": str(checkout / MILESTONES_PATH)}
        )
        self.processes.answer_corpus_change(checkout, (MILESTONES_PATH,), "docs(corpus): mark @MILESTONE.M6 reached")
        (checkout / "corpus").mkdir(parents=True)
        (checkout / MILESTONES_PATH).write_text(
            'MILESTONE M6\n\tTITLE "Hardening"\n\tSTATUS active\n', encoding="utf-8"
        )

        # Act
        written = write_answer(
            self.create_context("entity:REPORT", MILESTONE_REPORT, Configuration(worktree_root=worktree_root))
        )

        # Assert
        self.assertEqual(
            written,
            {
                "output": "entity:REPORT",
                "answer": str(self.run_directory / "answer.awawa"),
                "report": "corpus/milestones/M6-report.md",
                "branch": "integration/hardening",
                "pull_request": None,
            },
        )
