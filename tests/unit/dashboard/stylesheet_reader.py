import re
from importlib.resources import files

STYLESHEET = (files("brigade.dashboard") / "data" / "dashboard.css").read_text(encoding="utf-8")
LIGHT_BLOCK = re.compile(r"^:root \{\n(.*?)^\}\n", re.DOTALL | re.MULTILINE)
DARK_BLOCK = re.compile(
    r"^@media \(prefers-color-scheme: dark\) \{\n  :root \{\n(.*?)^  \}\n\}\n", re.DOTALL | re.MULTILINE
)
PROPERTY = re.compile(r"(--[\w-]+): ([^;]+);")
TONE_CLASS = re.compile(r"^\.tone-([\w-]+) \{\n  --tone: var\(--([\w-]+)\);\n\}", re.MULTILINE)
COLOUR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")


def read_light_properties() -> dict[str, str]:
    return dict(PROPERTY.findall(LIGHT_BLOCK.search(STYLESHEET).group(1)))


def read_dark_properties() -> dict[str, str]:
    return dict(PROPERTY.findall(DARK_BLOCK.search(STYLESHEET).group(1)))


def read_tone_classes() -> list[tuple[str, str]]:
    return TONE_CLASS.findall(STYLESHEET)


def read_colour_literals_of_the_views() -> list[str]:
    return COLOUR_LITERAL.findall(DARK_BLOCK.sub("", LIGHT_BLOCK.sub("", STYLESHEET)))
