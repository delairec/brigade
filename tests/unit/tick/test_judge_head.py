import unittest

from brigade.tick.commit_checks import CommandResult, CommitChecks
from brigade.tick.head_proof import ForgeCheck, HeadEvidence, HeadProof, TaskCheck
from brigade.tick.judge_head import judge_head

NO_FORGE_CHECK = ()
NO_TASK_CHECK = None
NO_COMMIT_CHECKS = None
NOTHING_FAILED = ()


class JudgeHeadTest(unittest.TestCase):
    def test_should_prove_green_a_head_whose_check_runs_of_the_forge_all_passed(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=(ForgeCheck(name="unit", verdict="success"), ForgeCheck(name="lint", verdict="success")),
            task_check=NO_TASK_CHECK,
            commit_checks=NO_COMMIT_CHECKS,
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="green", failed_commands=()))

    def test_should_prove_green_a_head_whose_task_check_of_that_commit_passed(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=NO_FORGE_CHECK,
            task_check=TaskCheck(head="c0ffee", failed_commands=NOTHING_FAILED),
            commit_checks=NO_COMMIT_CHECKS,
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="green", failed_commands=()))

    def test_should_not_take_a_passed_task_check_of_another_commit_as_proof(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=NO_FORGE_CHECK,
            task_check=TaskCheck(head="5e2a7c1", failed_commands=NOTHING_FAILED),
            commit_checks=NO_COMMIT_CHECKS,
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="unproven", failed_commands=()))

    def test_should_prove_green_a_head_whose_commands_the_tick_ran_all_passed(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=NO_FORGE_CHECK,
            task_check=NO_TASK_CHECK,
            commit_checks=CommitChecks(
                project="oak", commit="c0ffee", results=(CommandResult(command="npm test", exit_code=0),)
            ),
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="green", failed_commands=()))

    def test_should_wait_for_a_check_run_of_the_forge_pending_on_the_commit(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=(ForgeCheck(name="unit", verdict="pending"), ForgeCheck(name="lint", verdict="success")),
            task_check=NO_TASK_CHECK,
            commit_checks=NO_COMMIT_CHECKS,
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="pending", failed_commands=()))

    def test_should_name_red_the_check_runs_of_the_forge_that_failed_on_the_commit(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=(ForgeCheck(name="unit", verdict="failure"), ForgeCheck(name="lint", verdict="success")),
            task_check=NO_TASK_CHECK,
            commit_checks=NO_COMMIT_CHECKS,
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="red", failed_commands=("unit",)))

    def test_should_name_red_the_commands_of_the_task_check_that_failed_on_the_commit(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=NO_FORGE_CHECK,
            task_check=TaskCheck(head="c0ffee", failed_commands=("python3 -m unittest",)),
            commit_checks=NO_COMMIT_CHECKS,
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="red", failed_commands=("python3 -m unittest",)))

    def test_should_name_red_the_commands_the_tick_ran_that_failed_on_the_commit(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=NO_FORGE_CHECK,
            task_check=NO_TASK_CHECK,
            commit_checks=CommitChecks(
                project="oak",
                commit="c0ffee",
                results=(
                    CommandResult(command="npm ci", exit_code=0),
                    CommandResult(command="npm test", exit_code=1),
                ),
            ),
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="red", failed_commands=("npm test",)))

    def test_should_leave_unproven_a_head_with_no_check_run_and_no_record(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee", forge_checks=NO_FORGE_CHECK, task_check=NO_TASK_CHECK, commit_checks=NO_COMMIT_CHECKS
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="unproven", failed_commands=()))

    def test_should_prove_green_a_head_the_tick_checked_whatever_a_failed_check_run_of_the_forge(self):
        # Arrange
        evidence = HeadEvidence(
            commit="c0ffee",
            forge_checks=(ForgeCheck(name="unit", verdict="failure"),),
            task_check=NO_TASK_CHECK,
            commit_checks=CommitChecks(
                project="oak", commit="c0ffee", results=(CommandResult(command="npm test", exit_code=0),)
            ),
        )

        # Act
        proof = judge_head(evidence)

        # Assert
        self.assertEqual(proof, HeadProof(commit="c0ffee", state="green", failed_commands=()))
