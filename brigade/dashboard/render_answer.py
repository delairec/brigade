import json
from collections.abc import Callable

from brigade.dashboard.render_fragment import render_fragment
from brigade.dashboard.run_routed_command import OK, CommandAnswer


def render_answer(answer: CommandAnswer, render: Callable[[dict], str]) -> str:
    document = json.loads(answer.document)
    if answer.status != OK:
        return render_fragment(document)
    return render(document)
