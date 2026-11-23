from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Block:
    title: str
    lede: str
    body: str


def render_block(block: Block) -> str:
    lede = f"<p>{escape(block.lede, quote=False)}</p>" if block.lede else ""
    return (
        f'<section class="block"><div class="block-head"><h2>{escape(block.title)}</h2>{lede}</div>'
        f"{block.body}</section>"
    )
