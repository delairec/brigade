from brigade.checks._report_findings import report_findings
from brigade.runtime import Runtime

NAME = "forge_logins"
FORGE_LOGINS_COLLECTOR = "forge-logins"


def check(subject: dict, runtime: Runtime) -> dict:
    logins = subject["collected"][FORGE_LOGINS_COLLECTOR]["summary"]["logins"]
    findings = [
        f"gh printed no token for the login {login['login']}, bound to {', '.join(login['keys'])}"
        for login in logins
        if not login["token"]
    ]
    return report_findings(NAME, findings)
