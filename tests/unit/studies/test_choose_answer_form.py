import unittest

from brigade.studies.choose_answer_form import (
    PATTERN_ANSWER_FORM,
    REPORT_ANSWER_FORM,
    STUDY_ANSWER_FORM,
    TASK_REPORT_ANSWER_FORM,
    choose_answer_form,
)
from brigade.studies.convert_study import Study
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.task_report_order import TaskReportOrder
from tests.unit.studies.built_in_triage import BUILT_IN_TRIAGE

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
TASK_REPORT = Study(
    name="task-report",
    project="oak",
    question=None,
    collectors=(),
    slot="report",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
    task=TaskReportOrder(project="oak", task="B46", wave="oak_w4", branch="feature/B46-local-mode"),
)
RECORDED_STUDY_ANSWERING_REPORT = Study(
    name="trees",
    project="oak",
    question="how many trees?",
    collectors=("shell cmd=ls",),
    slot="review",
    every=None,
    output="entity:REPORT",
    answer_type="REPORT",
    status="active",
)


class ChooseAnswerFormTest(unittest.TestCase):
    def test_should_give_the_report_of_a_milestone_the_form_of_a_report(self):
        # Act
        form = choose_answer_form(MILESTONE_REPORT)

        # Assert
        self.assertEqual(form, REPORT_ANSWER_FORM)

    def test_should_give_the_report_of_a_task_the_form_of_the_report_of_a_task(self):
        # Act
        form = choose_answer_form(TASK_REPORT)

        # Assert
        self.assertEqual(form, TASK_REPORT_ANSWER_FORM)

    def test_should_name_the_report_of_a_task_after_its_project_and_its_task(self):
        # Act
        name = TASK_REPORT_ANSWER_FORM.name(TASK_REPORT, "20261103T100000Z-bbbbbb")

        # Assert
        self.assertEqual(name, "oak_B46")

    def test_should_give_a_study_the_user_recorded_the_form_of_a_study_whatever_type_it_answers(self):
        # Act
        form = choose_answer_form(RECORDED_STUDY_ANSWERING_REPORT)

        # Assert
        self.assertEqual(form, STUDY_ANSWER_FORM)

    def test_should_give_the_triage_the_form_of_patterns(self):
        # Act
        form = choose_answer_form(BUILT_IN_TRIAGE)

        # Assert
        self.assertEqual(form, PATTERN_ANSWER_FORM)

    def test_should_render_no_entity_for_the_slot_to_copy_in_the_form_of_patterns(self):
        # Arrange
        no_collected_evidence = []

        # Act
        rendered = PATTERN_ANSWER_FORM.render(None, BUILT_IN_TRIAGE, "20261019T090000Z-aaaaaa", no_collected_evidence)

        # Assert
        self.assertEqual(rendered, "")
