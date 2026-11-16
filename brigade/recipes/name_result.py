from brigade.recipes.run_order import OrderRun

RUN_ID_SEPARATOR = "-"
NAME_SEPARATOR = "_"


def name_result(run: OrderRun) -> str:
    return f"{run.order}{NAME_SEPARATOR}{run.run_id.replace(RUN_ID_SEPARATOR, NAME_SEPARATOR)}"
