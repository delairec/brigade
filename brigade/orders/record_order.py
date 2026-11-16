from dataclasses import dataclass

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.quote_awawa_string import quote_awawa_string
from brigade.runtime import Runtime

ORDERS_FILE = "orders.awawa"
ACTIVE_STATUS = "active"


@dataclass(frozen=True)
class NewOrder:
    name: str
    recipe: str
    project: str | None
    text: str | None
    params: tuple[str, ...]
    every: str | None


def _render_block(order: NewOrder) -> str:
    lines = [f"ORDER {order.name}", f"\tRECIPE {quote_awawa_string(order.recipe)}"]
    if order.project is not None:
        lines.append(f"\tPROJECT @PROJECT.{order.project}")
    if order.text is not None:
        lines.append(f"\tTEXT {quote_awawa_string(order.text)}")
    lines.extend(f"\tPARAM {quote_awawa_string(param)}" for param in order.params)
    if order.every is not None:
        lines.append(f"\tEVERY {quote_awawa_string(order.every)}")
    lines.append(f"\tSTATUS {ACTIVE_STATUS}")
    return "\n".join(lines) + "\n"


def _append_block(text: str, block: str) -> str:
    if not text.strip():
        return block
    return text.rstrip("\n") + "\n\n" + block


def record_order(runtime: Runtime, order: NewOrder) -> None:
    root = runtime.paths.config_root
    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=(ORDERS_FILE,),
            describe_message=lambda: f"brigade order new: @ORDER.{order.name}",
            rewrite=lambda texts: (_append_block(texts[0], _render_block(order)),),
        ),
    )
