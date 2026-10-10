from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.run_finished import RunFinished


@dataclass(frozen=True)
class RunMeasure:
    value: int | None
    partial: bool


def _measure_sum(reported: list[int | None]) -> RunMeasure:
    measured = [value for value in reported if value is not None]
    if not measured:
        return RunMeasure(value=None, partial=False)
    return RunMeasure(value=sum(measured), partial=len(measured) < len(reported))


@dataclass(frozen=True)
class FinishedRun:
    run: str
    finished_at: datetime
    segments: tuple[RunFinished, ...]

    @property
    def last(self) -> RunFinished:
        return self.segments[-1]

    @property
    def main_steps(self) -> RunMeasure:
        return _measure_sum([segment.main_steps for segment in self.segments])

    @property
    def oversized_output_steps(self) -> RunMeasure:
        return _measure_sum([segment.oversized_output_steps for segment in self.segments])

    @property
    def steps_to_first_edit(self) -> RunMeasure:
        reported = [segment.steps_to_first_edit for segment in self.segments]
        editing = next((index for index, value in enumerate(reported) if value is not None), None)
        if editing is None:
            return RunMeasure(value=None, partial=False)
        steps_before = sum(segment.main_steps or 0 for segment in self.segments[:editing])
        return RunMeasure(value=steps_before + reported[editing], partial=None in reported)
