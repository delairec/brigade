CHOOSERS = {"configuration": "config.toml", "probe": "the probe of the user systemd instance"}


def render_scheduler_install_text(document: dict) -> str:
    name = document["scheduler"]
    chooser = CHOOSERS[document["chosen_by"]]
    if document["keep_running"] is not None:
        lines = [f"{name} chosen by {chooser}: nothing installed; keep this command running", document["keep_running"]]
    else:
        lines = [f"{name} installed, chosen by {chooser}", *(f"unit  {unit}" for unit in document["unit_files"])]
        if document["cron_line"] is not None:
            lines.append(f"cron line  {document['cron_line']}")
    return "\n".join(lines)
