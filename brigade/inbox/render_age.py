UNITS = (("d", 86400), ("h", 3600), ("m", 60))
SECOND_UNIT = "s"


def render_age(age_s: int) -> str:
    for unit, seconds in UNITS:
        if age_s >= seconds:
            return f"{age_s // seconds}{unit}"
    return f"{age_s}{SECOND_UNIT}"
