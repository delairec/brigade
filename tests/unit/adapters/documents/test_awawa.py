import os
import tempfile
import unittest
from pathlib import Path

from brigade.adapters.documents.awawa import (
    create_document,
    describe_document,
    detect_entry,
    read_document,
    render_document,
)
from tests.awawa.provide_awawa import provide_awawa
from tests.create_process_runner import create_process_runner
from tests.unit.create_test_runtime import create_test_runtime

SCHEMA = (
    "SCHEMA ENTRY\n"
    '\tDESC "a step the run completed"\n'
    "\tFIELD DONE string\n"
    "\t\tREQUIRED\n"
    '\t\tDESC "what the step did, one line"\n'
    "\n"
    "SCHEMA HANDOVER\n"
    '\tDESC "the state of a run that hands over"\n'
    "\tFIELD NEXT string\n"
    "\t\tREQUIRED\n"
    '\t\tDESC "the step to resume at"\n'
)
TWO_ENTRIES = '\nENTRY e1\n\tDONE "read the task"\n\nENTRY e2\n\tDONE "wrote the tests"\n'
FRAME = ["one entry per major step", "never command output"]


class AwawaDocumentTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "progress.awawa"
        self.runtime = create_test_runtime(run_process=create_process_runner(os.environ["PATH"]))

    def describe_request(self, *, role_has_shell: bool = True) -> dict:
        return {
            "schema_version": 1,
            "document": "progress",
            "path": str(self.path),
            "schema": SCHEMA,
            "frame": FRAME,
            "shell": role_has_shell,
        }


class AwawaDocumentCreationTest(AwawaDocumentTestCase):
    def test_should_create_the_file_holding_its_schema_alone(self):
        # Act
        create_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(self.path.read_text(), SCHEMA)

    def test_should_answer_that_the_file_is_created(self):
        # Act
        answer = create_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(answer, {"schema_version": 1})


class AwawaDocumentDescriptionTest(AwawaDocumentTestCase):
    def test_should_name_the_file_the_types_of_its_schema_the_frame_and_the_checks_after_each_append(self):
        # Act
        description = describe_document(self.describe_request(role_has_shell=True), self.runtime)

        # Assert
        self.assertEqual(
            description,
            {
                "schema_version": 1,
                "text": f"The progress is the awawa corpus {self.path}: after the schema it holds, append one entity"
                " per entry, of a type the schema declares, named by the initial of its type in lower case and its"
                " rank among the entities of that type in order of writing.\n\n"
                "- ENTRY: a step the run completed\n"
                "- HANDOVER: the state of a run that hands over\n\n"
                "- one entry per major step\n"
                "- never command output\n\n"
                f"After each append, run awawa fmt {self.path} then awawa lint --strict {self.path}, naming the file"
                " and never its directory.\n",
            },
        )

    def test_should_ask_for_no_check_of_a_role_without_shell(self):
        # Act
        description = describe_document(self.describe_request(role_has_shell=False), self.runtime)

        # Assert
        self.assertEqual(
            description,
            {
                "schema_version": 1,
                "text": f"The progress is the awawa corpus {self.path}: after the schema it holds, append one entity"
                " per entry, of a type the schema declares, named by the initial of its type in lower case and its"
                " rank among the entities of that type in order of writing.\n\n"
                "- ENTRY: a step the run completed\n"
                "- HANDOVER: the state of a run that hands over\n\n"
                "- one entry per major step\n"
                "- never command output\n",
            },
        )


class AwawaDocumentEntryTest(AwawaDocumentTestCase):
    def test_should_answer_whether_the_file_holds_an_entry_beyond_its_schema(self):
        for content, holds_entry in [
            (SCHEMA, False),
            (f"{SCHEMA}\n// a note\n", False),
            (f'{SCHEMA}\nENTRY e1\n\tDONE "read the task"\n', True),
            (f"{SCHEMA}garbage here\n", True),
        ]:
            with self.subTest(content=content):
                # Arrange
                self.path.write_text(content)

                # Act
                answer = detect_entry(self.describe_request(), self.runtime)

                # Assert
                self.assertEqual(answer, {"schema_version": 1, "holds_entry": holds_entry})


class AwawaDocumentReadingTest(AwawaDocumentTestCase):
    def setUp(self):
        super().setUp()
        self.runtime = create_test_runtime(run_process=create_process_runner(provide_awawa(self)))

    def test_should_give_a_resuming_run_the_inventory_of_each_type_and_the_last_entity(self):
        # Arrange
        self.path.write_text(SCHEMA + TWO_ENTRIES)

        # Act
        reading = read_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(
            reading,
            {
                "schema_version": 1,
                "text": f"$ awawa status ENTRY {self.path}\n"
                "ENTRY (2):\n"
                f"  @ENTRY.e1  (none)  {self.path}:13  incoming 0\n"
                f"  @ENTRY.e2  (none)  {self.path}:16  incoming 0\n\n"
                f"$ awawa status HANDOVER {self.path}\n"
                "HANDOVER (0):\n\n"
                f"$ awawa show @ENTRY.e2 {self.path}\n"
                "ENTRY e2\n"
                '\tDONE "wrote the tests"\n',
            },
        )

    def test_should_give_a_resuming_run_the_empty_inventory_of_each_type_of_a_file_holding_no_entity(self):
        # Arrange
        self.path.write_text(SCHEMA)

        # Act
        reading = read_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(
            reading,
            {
                "schema_version": 1,
                "text": f"$ awawa status ENTRY {self.path}\n"
                "ENTRY (0):\n\n"
                f"$ awawa status HANDOVER {self.path}\n"
                "HANDOVER (0):\n",
            },
        )

    def test_should_format_the_file_before_reading_it(self):
        # Arrange
        self.path.write_text(f'{SCHEMA}ENTRY e1\n  DONE "read the task"\n')

        # Act
        read_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(self.path.read_text(), f'{SCHEMA}\nENTRY e1\n\tDONE "read the task"\n')

    def test_should_open_on_the_lint_output_the_instruction_to_rewrite_and_the_file_whole_when_lint_fails(self):
        # Arrange
        self.path.write_text(f'{SCHEMA}\nENTRY e1\n\tNEXT "section 3"\n')

        # Act
        reading = read_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(
            reading,
            {
                "schema_version": 1,
                "text": f"$ awawa lint --strict {self.path}\n"
                f"{self.path} — 2 error(s), 0 warning(s)\n"
                f"L003  error  {self.path}:14:2\n"
                "      field NEXT is not declared on ENTRY\n"
                f"L006  error  {self.path}:13:1\n"
                "      required field DONE is absent from ENTRY\n\n"
                f"Rewrite {self.path} so that awawa lint --strict {self.path} passes, keeping every entry."
                " The file as it is:\n\n"
                f'{SCHEMA}\nENTRY e1\n\tNEXT "section 3"\n',
            },
        )


class AwawaDocumentRenderingTest(AwawaDocumentTestCase):
    def setUp(self):
        super().setUp()
        self.runtime = create_test_runtime(run_process=create_process_runner(provide_awawa(self)))

    def test_should_render_each_entity_as_readable_text_and_as_entities(self):
        # Arrange
        self.path.write_text(SCHEMA + TWO_ENTRIES)

        # Act
        rendering = render_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(
            rendering,
            {
                "schema_version": 1,
                "text": "ENTRY e1\n  DONE: read the task\n\nENTRY e2\n  DONE: wrote the tests\n",
                "entities": [
                    {"type": "ENTRY", "name": "e1", "fields": [{"name": "DONE", "value": "read the task"}]},
                    {"type": "ENTRY", "name": "e2", "fields": [{"name": "DONE", "value": "wrote the tests"}]},
                ],
            },
        )

    def test_should_render_a_backslash_awawa_keeps_as_it_holds_it(self):
        # Arrange
        self.path.write_text(SCHEMA + '\nENTRY e1\n\tDONE "matched grep a\\.b"\n')

        # Act
        rendering = render_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(
            rendering,
            {
                "schema_version": 1,
                "text": "ENTRY e1\n  DONE: matched grep a\\.b\n",
                "entities": [
                    {"type": "ENTRY", "name": "e1", "fields": [{"name": "DONE", "value": "matched grep a\\.b"}]}
                ],
            },
        )

    def test_should_render_the_entities_of_a_file_whose_schema_lives_beside_it(self):
        # Arrange
        (self.path.parent / "_schema.awawa").write_text(SCHEMA)
        self.path.write_text('ENTRY e1\n\tDONE "read the task"\n')

        # Act
        rendering = render_document({"path": str(self.path)}, self.runtime)

        # Assert
        self.assertEqual(
            rendering,
            {
                "schema_version": 1,
                "text": "ENTRY e1\n  DONE: read the task\n",
                "entities": [{"type": "ENTRY", "name": "e1", "fields": [{"name": "DONE", "value": "read the task"}]}],
            },
        )

    def test_should_render_a_file_lint_refuses_as_its_raw_text_with_no_entities(self):
        # Arrange
        self.path.write_text(SCHEMA + '\nENTRY e1\n\tDONE "read the task"\n\nENTRY e2\n\tNEXT "section 3"\n')

        # Act
        rendering = render_document(self.describe_request(), self.runtime)

        # Assert
        self.assertEqual(
            rendering,
            {
                "schema_version": 1,
                "text": f'{SCHEMA}\nENTRY e1\n\tDONE "read the task"\n\nENTRY e2\n\tNEXT "section 3"\n',
                "entities": None,
            },
        )


class AwawaDocumentDescriptionOfASchemaHoldingABackslashTest(AwawaDocumentTestCase):
    def test_should_name_the_type_with_the_backslash_its_description_keeps(self):
        # Arrange
        request = {
            **self.describe_request(role_has_shell=False),
            "schema": 'SCHEMA ENTRY\n\tDESC "a step of grep a\\.b"\n',
        }

        # Act
        description = describe_document(request, self.runtime)

        # Assert
        self.assertEqual(
            description,
            {
                "schema_version": 1,
                "text": f"The progress is the awawa corpus {self.path}: after the schema it holds, append one entity"
                " per entry, of a type the schema declares, named by the initial of its type in lower case and its"
                " rank among the entities of that type in order of writing.\n\n"
                "- ENTRY: a step of grep a\\.b\n\n"
                "- one entry per major step\n"
                "- never command output\n",
            },
        )
