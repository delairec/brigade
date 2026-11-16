from dataclasses import dataclass

from brigade.system.transcripts_answer import TranscriptMessage, TranscriptsAnswer

STEP_BEFORE_ANY_TOOL_CALL = 1


@dataclass(frozen=True)
class SessionSteps:
    main_turns: int
    total_turns: int


def _count_steps(messages: tuple[TranscriptMessage, ...]) -> int:
    return sum(message.tool_calls for message in messages) + STEP_BEFORE_ANY_TOOL_CALL


def count_session_steps(transcripts: TranscriptsAnswer) -> SessionSteps:
    main_turns = _count_steps(transcripts.messages)
    subagent_steps = sum(_count_steps(subagent.messages) for subagent in transcripts.subagents)
    return SessionSteps(main_turns=main_turns, total_turns=main_turns + subagent_steps)
