import unittest

from brigade.studies.choose_answer_form import REPORT_ANSWER_FORM, STUDY_ANSWER_FORM, choose_answer_form
from brigade.studies.convert_study import Study

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
    def test_should_give_the_report_of_a_wave_the_form_of_a_report(self):
        # Act
        form = choose_answer_form(WAVE_REPORT)

        # Assert
        self.assertEqual(form, REPORT_ANSWER_FORM)

    def test_should_give_a_study_the_user_recorded_the_form_of_a_study_whatever_type_it_answers(self):
        # Act
        form = choose_answer_form(RECORDED_STUDY_ANSWERING_REPORT)

        # Assert
        self.assertEqual(form, STUDY_ANSWER_FORM)
