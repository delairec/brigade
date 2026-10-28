from brigade.system.parse_configuration import Configuration


def choose_dashboard_port(requested_port: int | None, configuration: Configuration) -> int:
    return configuration.dashboard_port if requested_port is None else requested_port
