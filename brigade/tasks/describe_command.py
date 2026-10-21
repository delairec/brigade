from brigade.system.run_process import ProcessRecord


def describe_command(record: ProcessRecord) -> dict:
    return {
        "command": " ".join(record.argv),
        "exit_code": record.exit_code,
        "stderr": record.stderr,
        "output": record.stdout,
    }
