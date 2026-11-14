from dataclasses import dataclass

from brigade.corpus.locate_entity_block import locate_entity_block

PATTERN_TYPE = "PATTERN"
HEADER_PREFIX = f"{PATTERN_TYPE} "


@dataclass(frozen=True)
class FoldedAnswer:
    held: str
    new: str


def _list_names(lines: list[str]) -> list[str]:
    return [line.rstrip().removeprefix(HEADER_PREFIX) for line in lines if line.startswith(HEADER_PREFIX)]


def _locate_content(lines: list[str], name: str) -> range:
    block = locate_entity_block(lines, PATTERN_TYPE, name)
    end = block.stop
    while not lines[end - 1].strip():
        end -= 1
    return range(block.start, end)


def fold_pattern_answer(held: str, answer: str) -> FoldedAnswer:
    held_lines = held.splitlines(keepends=True)
    answer_lines = [f"{line}\n" for line in answer.splitlines()]
    folded_names = [name for name in _list_names(answer_lines) if name in _list_names(held_lines)]
    for name in folded_names:
        added = _locate_content(answer_lines, name)
        content = _locate_content(held_lines, name)
        held_lines[content.stop : content.stop] = answer_lines[added.start + 1 : added.stop]
    folded_lines = {index for name in folded_names for index in locate_entity_block(answer_lines, PATTERN_TYPE, name)}
    new_lines = [line for index, line in enumerate(answer_lines) if index not in folded_lines]
    return FoldedAnswer(held="".join(held_lines), new="".join(new_lines))
