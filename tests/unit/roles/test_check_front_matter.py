import unittest

from brigade.roles.check_front_matter import RoleProblem, check_front_matter

DECLARED = {
    "name": "ada",
    "slot": "plan",
    "work": "plans the waves",
    "reasoning": "deep",
    "capabilities": "read, shell",
    "budget": "40",
    "returns": "the wave plan",
}


class CheckFrontMatterTest(unittest.TestCase):
    def test_should_find_nothing_in_a_front_matter_declaring_every_key_within_its_set(self):
        # Act
        problems = check_front_matter(DECLARED)

        # Assert
        self.assertEqual(problems, ())

    def test_should_name_the_key_of_each_problem(self):
        rows = [
            ("a model named", {**DECLARED, "model": "opus"}, RoleProblem(key="model", problem="names a model")),
            (
                "an unknown key",
                {**DECLARED, "colour": "blue"},
                RoleProblem(key="colour", problem="is not a declared key"),
            ),
            (
                "a reasoning level outside its set",
                {**DECLARED, "reasoning": "huge"},
                RoleProblem(key="reasoning", problem="is huge, not one of deepest, deep, standard, light"),
            ),
            (
                "a capability outside its set",
                {**DECLARED, "capabilities": "read, fly"},
                RoleProblem(key="capabilities", problem="is fly, not one of read, write, shell, net"),
            ),
            (
                "a slot outside its set",
                {**DECLARED, "slot": "cook"},
                RoleProblem(
                    key="slot",
                    problem="is cook, not one of plan, build, review, remediate, rebase, report, triage, rules, explore",
                ),
            ),
            (
                "a budget that is no count of steps",
                {**DECLARED, "budget": "lots"},
                RoleProblem(key="budget", problem="is lots, not a positive integer"),
            ),
            ("an empty value", {**DECLARED, "returns": ""}, RoleProblem(key="returns", problem="is empty")),
        ]
        for case, front_matter, expected_problem in rows:
            with self.subTest(case=case):
                # Act
                problems = check_front_matter(front_matter)

                # Assert
                self.assertEqual(problems, (expected_problem,))

    def test_should_name_every_declared_key_missing(self):
        # Arrange
        name_only = {"name": "ada"}

        # Act
        problems = check_front_matter(name_only)

        # Assert
        self.assertEqual(
            problems,
            (
                RoleProblem(key="slot", problem="is missing"),
                RoleProblem(key="work", problem="is missing"),
                RoleProblem(key="reasoning", problem="is missing"),
                RoleProblem(key="capabilities", problem="is missing"),
                RoleProblem(key="budget", problem="is missing"),
                RoleProblem(key="returns", problem="is missing"),
            ),
        )
