from collections.abc import Iterable
from dataclasses import fields

from brigade.system.token_usage import TokenUsage


def sum_token_usage(usages: Iterable[TokenUsage | None]) -> TokenUsage | None:
    reported = [usage for usage in usages if usage is not None]
    if not reported:
        return None
    return TokenUsage(
        **{count.name: sum(getattr(usage, count.name) for usage in reported) for count in fields(TokenUsage)}
    )
