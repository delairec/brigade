from brigade.system.run_process import ProcessRecord


def describe_command_record(command: str, record: ProcessRecord) -> dict:
    return {
        "command": command,
        "exit_code": record.exit_code,
        "duration_ms": record.duration_ms,
        "output": f"{record.stdout}{record.stderr}",
    }
