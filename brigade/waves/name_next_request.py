import re


def name_next_request(text: str, project: str) -> str:
    declaration = re.compile(rf"^REQUEST {re.escape(project)}_(\d+)$", re.MULTILINE)
    highest = max((int(number) for number in declaration.findall(text)), default=0)
    return f"{project}_{highest + 1}"
