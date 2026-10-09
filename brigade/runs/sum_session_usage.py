from brigade.system.token_usage import TokenUsage
from brigade.system.transcripts_answer import TranscriptsAnswer

USAGE_COUNTERS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def sum_session_usage(transcripts: TranscriptsAnswer) -> TokenUsage:
    messages = [
        *transcripts.messages,
        *(message for subagent in transcripts.subagents for message in subagent.messages),
    ]
    usage_by_id = {message.id: message.usage for message in messages if message.usage is not None}
    return TokenUsage(
        **{counter: sum(getattr(usage, counter) for usage in usage_by_id.values()) for counter in USAGE_COUNTERS}
    )
