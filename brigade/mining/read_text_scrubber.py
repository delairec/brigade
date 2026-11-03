import functools
import re
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entities import read_entities
from brigade.mining.scrubbing_rule import ScrubbingRule
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.check_privacy import BUILT_IN_PATTERNS
from brigade.verify.read_privacy_patterns import read_privacy_patterns

PRIVATE_MARKER = "[private]"
NO_PUBLIC_PATTERN = ()
PROJECT_TYPE = "PROJECT"
TOKEN_SHAPES = (
    (re.compile(r"\bgh[pos]_\w+"), "a GitHub token"),
    (re.compile(r"\bgithub_pat_\w+"), "a GitHub token"),
    (re.compile(r"\bsk-ant-[\w-]+"), "an Anthropic API key"),
)


def _list_rules(run_process: Callable[[ProcessRequest], ProcessRecord], config_root: Path) -> list[ScrubbingRule]:
    rules = [
        ScrubbingRule(pattern, f"[{description.partition(' ')[2]}]", NO_PUBLIC_PATTERN)
        for pattern, description in (*TOKEN_SHAPES, *BUILT_IN_PATTERNS)
    ]
    for project in read_entities(run_process, config_root, PROJECT_TYPE):
        patterns = read_privacy_patterns(project)
        public = tuple(re.compile(pattern) for pattern in patterns.public)
        rules.extend(ScrubbingRule(re.compile(pattern), PRIVATE_MARKER, public) for pattern in patterns.private)
    return rules


def _scrub_text(text: str, rules: list[ScrubbingRule]) -> str:
    for rule in rules:
        text = rule.scrub(text)
    return text


def read_text_scrubber(
    run_process: Callable[[ProcessRequest], ProcessRecord], config_root: Path
) -> Callable[[str], str]:
    return functools.partial(_scrub_text, rules=_list_rules(run_process, config_root))
