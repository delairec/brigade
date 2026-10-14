from importlib.resources import files

SHIPPED_DATA = files("brigade.corpus") / "data"
SHIPPED_SCHEMA = SHIPPED_DATA / "schema.awawa.tpl"
