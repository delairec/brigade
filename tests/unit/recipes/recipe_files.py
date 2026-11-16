from pathlib import Path


def write_recipe(directory: Path, name: str, description: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.toml").write_text(
        f'schema_version = 1\nname = "{name}"\ndescription = "{description}"\nparams = []\nmax_wall = 5\nsteps = []\n'
    )
