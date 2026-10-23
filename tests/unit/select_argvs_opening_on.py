def select_argvs_opening_on(argvs: list[tuple[str, ...]], *prefixes: tuple[str, ...]) -> list[tuple[str, ...]]:
    return [argv for argv in argvs if any(argv[: len(prefix)] == prefix for prefix in prefixes)]
