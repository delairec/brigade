import unittest

from brigade.studies.fold_pattern_answer import FoldedAnswer, fold_pattern_answer

HELD = (
    'PATTERN cli_is_hard_to_read\n\tTITLE "the cli is hard to read"\n\tSTATUS ratified\n\n'
    'PATTERN tick_is_slow\n\tTITLE "the tick is slow"\n\tSTATUS new\n'
)
NEW_PATTERN = 'PATTERN lint_is_noisy\n\tTITLE "the lint is noisy"\n\tSTATUS new\n\tEVIDENCE "rt:7"\n\tACTION wave\n'


class FoldPatternAnswerTest(unittest.TestCase):
    def test_should_add_the_evidence_to_the_held_pattern_and_keep_the_new_ones_to_append(self):
        # Arrange
        answer = f'PATTERN tick_is_slow\n\tEVIDENCE "rt:101"\n\n{NEW_PATTERN}'

        # Act
        folded = fold_pattern_answer(HELD, answer)

        # Assert
        self.assertEqual(
            folded,
            FoldedAnswer(
                held='PATTERN cli_is_hard_to_read\n\tTITLE "the cli is hard to read"\n\tSTATUS ratified\n\n'
                'PATTERN tick_is_slow\n\tTITLE "the tick is slow"\n\tSTATUS new\n\tEVIDENCE "rt:101"\n',
                new=NEW_PATTERN,
            ),
        )

    def test_should_end_each_evidence_added_on_a_line_of_its_own_when_the_answer_has_no_final_newline(self):
        # Arrange
        answer_without_final_newline = 'PATTERN cli_is_hard_to_read\n\tEVIDENCE "rt:101"'

        # Act
        folded = fold_pattern_answer(HELD, answer_without_final_newline)

        # Assert
        self.assertEqual(
            folded.held,
            'PATTERN cli_is_hard_to_read\n\tTITLE "the cli is hard to read"\n\tSTATUS ratified\n\tEVIDENCE "rt:101"\n\n'
            'PATTERN tick_is_slow\n\tTITLE "the tick is slow"\n\tSTATUS new\n',
        )
