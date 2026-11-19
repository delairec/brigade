import functools
import threading
import unittest

from brigade.dashboard.awawa_addon_supervisor import AddonAnswer, AwawaAddonSupervisor
from brigade.errors import BrigadeError, ToolNotFound
from tests.unit.dashboard.addon_child_double import ChildStarterDouble, PipedChildDouble, answer_with_the_message

HOLDERS = frozenset({"app"})
NO_HOLDER = frozenset()
ANSWER_TIMEOUT_S = 5.0
SHORT_TIMEOUT_S = 0.05
BOARD_QUERY = {"view": "board", "type": "TASK"}


def answer_with_no_document(message: dict) -> dict:
    return {"view": "board"}


def exit_while_answering(message: dict) -> dict:
    raise SystemExit


def answer_with_an_error(message: dict) -> dict:
    return {"error": "no worktree of @PROJECT.app has the branch b42 checked out"}


def create_blocked_answer(test_case: unittest.TestCase):
    released = threading.Event()
    test_case.addCleanup(released.set)

    def answer_once_released(message: dict) -> dict:
        released.wait()
        return {"document": {}}

    return answer_once_released


def refuse_to_start():
    raise ToolNotFound("python3 not on PATH")


class HolderListingDouble:
    def __init__(self, *outcomes: frozenset[str] | BrigadeError):
        self.outcomes = list(outcomes)
        self.calls = 0

    def list(self) -> frozenset[str]:
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, BrigadeError):
            raise outcome
        return outcome


def create_supervisor(test_case, starter, holders=HOLDERS, timeout_s=ANSWER_TIMEOUT_S) -> AwawaAddonSupervisor:
    supervisor = AwawaAddonSupervisor(lambda: holders, starter.start, timeout_s)
    test_case.addCleanup(supervisor.stop)
    return supervisor


class OpenAwawaAddonTest(unittest.TestCase):
    def test_should_start_one_child_when_a_project_holds_a_corpus(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = create_supervisor(self, starter)

        # Act
        supervisor.open()

        # Assert
        self.assertEqual(len(starter.children), 1)

    def test_should_start_no_child_when_no_project_holds_a_corpus(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = create_supervisor(self, starter, holders=NO_HOLDER)

        # Act
        supervisor.open()

        # Assert
        self.assertEqual(starter.children, [])


class AskAwawaAddonTest(unittest.TestCase):
    def test_should_relay_the_request_over_the_pipes_and_answer_its_document(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = create_supervisor(self, starter)
        supervisor.open()

        # Act
        answer = supervisor.ask("app", BOARD_QUERY)

        # Assert
        self.assertEqual(
            answer, AddonAnswer(status=200, document={"asked": {"project": "app", "view": "board", "type": "TASK"}})
        )
        self.assertEqual(len(starter.children), 1)

    def test_should_answer_a_project_holding_no_corpus_without_asking_the_child(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = create_supervisor(self, starter)

        # Act
        answer = supervisor.ask("shop", BOARD_QUERY)

        # Assert
        self.assertEqual(answer, AddonAnswer(status=404, document={"error": "@PROJECT.shop holds no awawa corpus"}))
        self.assertEqual(starter.children, [])

    def test_should_answer_the_error_the_child_answers(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_an_error))
        supervisor = create_supervisor(self, starter)

        # Act
        answer = supervisor.ask("app", BOARD_QUERY)

        # Assert
        self.assertEqual(
            answer,
            AddonAnswer(status=500, document={"error": "no worktree of @PROJECT.app has the branch b42 checked out"}),
        )


class AskADeadAwawaAddonTest(unittest.TestCase):
    def test_should_start_the_dead_child_again_at_the_next_request(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = create_supervisor(self, starter)
        supervisor.open()
        starter.children[0].die()

        # Act
        answer = supervisor.ask("app", BOARD_QUERY)

        # Assert
        self.assertEqual(answer.status, 200)
        self.assertEqual(len(starter.children), 2)

    def test_should_answer_that_the_addon_stopped_when_the_child_dies_during_the_request(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, exit_while_answering))
        supervisor = create_supervisor(self, starter)
        supervisor.open()
        child = starter.children[0]

        # Act
        answer = supervisor.ask("app", BOARD_QUERY)

        # Assert
        self.assertEqual(
            answer,
            AddonAnswer(status=503, document={"error": "the awawa addon stopped; the next request starts it again"}),
        )
        self.assertFalse(child.is_running())

    def test_should_stop_a_child_answering_nothing_within_the_timeout_and_start_it_at_the_next_request(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, create_blocked_answer(self)))
        supervisor = create_supervisor(self, starter, timeout_s=SHORT_TIMEOUT_S)
        supervisor.open()

        # Act
        answers = (supervisor.ask("app", BOARD_QUERY), supervisor.ask("app", BOARD_QUERY))

        # Assert
        self.assertEqual(
            answers[0],
            AddonAnswer(
                status=503,
                document={"error": "the awawa addon answered nothing within 0.05 s; the next request starts it again"},
            ),
        )
        self.assertFalse(starter.children[0].is_running())
        self.assertEqual(len(starter.children), 2)

    def test_should_stop_a_child_answering_no_document(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_no_document))
        supervisor = create_supervisor(self, starter)

        # Act
        answer = supervisor.ask("app", BOARD_QUERY)

        # Assert
        self.assertEqual(
            answer,
            AddonAnswer(
                status=503, document={"error": "the awawa addon answered no document; the next request starts it again"}
            ),
        )
        self.assertFalse(starter.children[0].is_running())


class AskAnAwawaAddonFailingAtItsStartTest(unittest.TestCase):
    def test_should_report_the_error_of_the_start_and_try_one_start_per_request(self):
        # Arrange
        failing = functools.partial(
            PipedChildDouble,
            answer_with_the_message,
            ready_line=None,
            failure="brigade awawa-addon: awawa not on PATH",
        )
        starter = ChildStarterDouble(failing)
        supervisor = create_supervisor(self, starter)
        supervisor.open()

        # Act
        answers = (supervisor.ask("app", BOARD_QUERY), supervisor.ask("app", BOARD_QUERY))

        # Assert
        self.assertEqual(
            answers,
            (
                AddonAnswer(
                    status=503,
                    document={"error": "the awawa addon did not start: brigade awawa-addon: awawa not on PATH"},
                ),
                AddonAnswer(
                    status=503,
                    document={"error": "the awawa addon did not start: brigade awawa-addon: awawa not on PATH"},
                ),
            ),
        )
        self.assertEqual(len(starter.children), 3)
        self.assertFalse(starter.children[0].is_running())

    def test_should_report_a_first_line_that_is_not_its_start(self):
        for case, ready_line in (("a line that is not json", "Traceback"), ("a json that is no object", "1")):
            with self.subTest(case=case):
                # Arrange
                starter = ChildStarterDouble(
                    functools.partial(
                        PipedChildDouble, answer_with_the_message, ready_line=ready_line, failure="exited"
                    )
                )
                supervisor = create_supervisor(self, starter)

                # Act
                answer = supervisor.ask("app", BOARD_QUERY)

                # Assert
                self.assertEqual(
                    answer, AddonAnswer(status=503, document={"error": "the awawa addon did not start: exited"})
                )

    def test_should_report_a_child_that_could_not_be_launched(self):
        # Arrange
        supervisor = AwawaAddonSupervisor(lambda: HOLDERS, refuse_to_start, ANSWER_TIMEOUT_S)

        # Act
        answer = supervisor.ask("app", BOARD_QUERY)

        # Assert
        self.assertEqual(
            answer, AddonAnswer(status=503, document={"error": "the awawa addon did not start: python3 not on PATH"})
        )


class AskAnAwawaAddonWhoseHoldersCouldNotBeListedTest(unittest.TestCase):
    def test_should_report_the_error_of_the_listing_and_list_again_at_each_request(self):
        # Arrange
        listing = HolderListingDouble(ToolNotFound("awawa not on PATH"))
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = AwawaAddonSupervisor(listing.list, starter.start, ANSWER_TIMEOUT_S)
        supervisor.open()

        # Act
        answers = (supervisor.ask("app", BOARD_QUERY), supervisor.ask("app", BOARD_QUERY))

        # Assert
        unavailable = AddonAnswer(status=503, document={"error": "the awawa addon did not start: awawa not on PATH"})
        self.assertEqual(answers, (unavailable, unavailable))
        self.assertEqual(listing.calls, 3)
        self.assertEqual(starter.children, [])

    def test_should_serve_once_a_later_request_lists_the_holders(self):
        # Arrange
        listing = HolderListingDouble(ToolNotFound("awawa not on PATH"), HOLDERS)
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = AwawaAddonSupervisor(listing.list, starter.start, ANSWER_TIMEOUT_S)
        self.addCleanup(supervisor.stop)
        supervisor.open()

        # Act
        answers = (supervisor.ask("app", BOARD_QUERY), supervisor.ask("app", BOARD_QUERY))

        # Assert
        self.assertEqual([answer.status for answer in answers], [200, 200])
        self.assertEqual(listing.calls, 2)


class StopAwawaAddonTest(unittest.TestCase):
    def test_should_stop_the_child(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = AwawaAddonSupervisor(lambda: HOLDERS, starter.start, ANSWER_TIMEOUT_S)
        supervisor.open()

        # Act
        supervisor.stop()

        # Assert
        self.assertFalse(starter.children[0].is_running())

    def test_should_stop_nothing_when_no_child_runs(self):
        # Arrange
        starter = ChildStarterDouble(functools.partial(PipedChildDouble, answer_with_the_message))
        supervisor = AwawaAddonSupervisor(lambda: NO_HOLDER, starter.start, ANSWER_TIMEOUT_S)

        # Act
        supervisor.stop()

        # Assert
        self.assertEqual(starter.children, [])
