import re
from pathlib import Path

_LINK_TARGET = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _read_linked_pages(text: str) -> list[str]:
    return [
        target.partition("#")[0]
        for target in _LINK_TARGET.findall(text)
        if "://" not in target and not target.startswith("#")
    ]


def find_wiki_link_defects(wiki_root: Path) -> list[str]:
    texts = {path.name: path.read_text(encoding="utf-8") for path in sorted(wiki_root.glob("*.md"))}
    linked_from_home = set(_read_linked_pages(texts["Home.md"]))
    linked_from_sidebar = set(_read_linked_pages(texts["_Sidebar.md"]))
    return (
        [
            f"{name} links {linked}, which is no page of wiki/"
            for name, text in texts.items()
            for linked in _read_linked_pages(text)
            if linked not in texts
        ]
        + [
            f"{name} is not linked from Home.md"
            for name in texts
            if name != "Home.md" and not name.startswith("_") and name not in linked_from_home
        ]
        + [
            f"{name} is not linked from _Sidebar.md"
            for name in texts
            if not name.startswith("_") and name not in linked_from_sidebar
        ]
    )
