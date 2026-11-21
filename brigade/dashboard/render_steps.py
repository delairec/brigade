def render_steps(steps: tuple[str, ...]) -> str:
    return f'<ol class="steps">{"".join(f"<li><p>{step}</p></li>" for step in steps)}</ol>'
