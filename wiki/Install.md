Answers how to install brigade, from a clone or as a single file, what it needs on the machine, how `brigade doctor` checks that machine and how `brigade init` creates the operational corpus and `config.toml`.

brigade needs Python 3.11.4 or later and nothing outside its standard library.

## From a clone

From a clone, link the entry point into a directory on your `PATH`; brigade then runs from any working directory:

```
git clone https://github.com/delairec/brigade.git
mkdir -p ~/.local/bin
ln -s "$PWD/brigade/bin/brigade" ~/.local/bin/brigade
brigade --version
```

## As a single file

Build the single-file zipapp, which needs `python3` alone, and run or copy `dist/brigade.pyz`:

```
python3 build.py
python3 dist/brigade.pyz --version
```

## Below the Python floor

Below Python 3.11.4, brigade exits non-zero and names the version it needs and the version it found.

## Check the machine: `brigade doctor`

`brigade doctor` (or `brigade doctor --json`) tells whether brigade can run on the machine: Python 3.11.4 or later, git,
awawa 2.7 or later and the probe of the client adapter `config.toml` names are checked, a missing one is a finding and
the exit code is 1; a user systemd instance, the linger of the user, read from `loginctl show-user -p Linger`
where the scheduler is `systemd` as `scheduler install` chooses it, without which the timer stops at logout, gh
and the account it is logged in as, awawa-web and the instructions corpus `config.toml` names, `awawa lint --strict`
clean or not, are optional, each reported with its fallback, a missing one a warning; so is an installed
`_schema.awawa` that differs from the shipped one: brigade supports no operational corpus of an older schema,
throw it away and run `brigade init` again, then register the projects anew. A `POLICY` that sets `REVIEW approval`,
`verdict` by default, is a warning naming its project while the `build` and `review` slots of `[forge_accounts]` are not
bound to two distinct logins: GitHub refuses an approval by the author of a pull request. A `config.toml` that is not
TOML is reported with the error of its one read on every line that needs it, the client, gh, its logins, the review mode
and the instructions corpus, and gh is not run.

## Create the operational corpus: `brigade init`

`brigade init` (or `brigade init --json`) creates the operational corpus in `$XDG_CONFIG_HOME/brigade/`,
`~/.config/brigade/` by default: a git repository holding `_schema.awawa` and a `.gitignore`, committed with your git
identity, and `config.toml`, the machine configuration, every key commented out and never committed. It needs
`user.name` and `user.email` set in git. Run again, it rewrites nothing: a file that differs from the shipped one is
left as it is and reported as a warning.
