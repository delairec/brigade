from brigade.system.retired_name import RetiredName

RETIRED_KEYS = {"seconds_per_step": "seconds_per_turn", "document": "progress_form", "journal_poll_s": "log_poll_s"}


def find_retired_configuration_keys(document: dict) -> list[RetiredName]:
    return [RetiredName(old=key, new=RETIRED_KEYS[key]) for key in document if key in RETIRED_KEYS]
