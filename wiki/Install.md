How to install brigade, check the machine with `brigade doctor`, and create the operational corpus and `config.toml`
with `brigade init`.

brigade needs Python 3.11.4 or later and nothing outside its standard library.

## Install

From a clone, link the entry point into a directory on your `PATH`; brigade then runs from any working directory:

```
git clone https://github.com/delairec/brigade.git
mkdir -p ~/.local/bin
ln -s "$PWD/brigade/bin/brigade" ~/.local/bin/brigade
brigade --version
```

Or build the single-file zipapp, which needs `python3` alone, and run or copy `dist/brigade.pyz`:

```
python3 build.py
python3 dist/brigade.pyz --version
```

> **Watch out:** below Python 3.11.4, brigade exits non-zero and names the version it needs and the version it found.

## Check the machine: `brigade doctor`

```
brigade doctor          # exit 1 when a required item is missing
brigade doctor --json
```

`brigade doctor` tells whether brigade can run on the machine. A missing required item is a finding and the exit code
is 1; a missing optional item is a warning, reported with its fallback.

| Item | Required |
|---|---|
| Python 3.11.4 or later | yes |
| git | yes |
| awawa 2.7 or later | yes |
| the probe of the client adapter `config.toml` names | yes |
| a user systemd instance | no |
| the linger of the user, read from `loginctl show-user -p Linger` where the scheduler is `systemd` as `scheduler install` chooses it: without it the timer stops at logout | no |
| gh and the account it is logged in as | no |
| awawa-web | no |
| the instructions corpus `config.toml` names, `awawa lint --strict` clean or not | no |
| an installed `_schema.awawa` identical to the shipped one | no |

> **Watch out:** an installed `_schema.awawa` that differs from the shipped one is only a warning, yet brigade supports
> no operational corpus of an older schema: throw it away and run `brigade init` again, then register the projects anew.

<details><summary>Rarer warnings of <code>brigade doctor</code></summary>

- A `POLICY` that sets `REVIEW approval` (`verdict` by default) is a warning naming its project while the `build` and
  `review` slots of `[forge_accounts]` are not bound to two distinct logins: GitHub refuses an approval by the author
  of a pull request.
- A `config.toml` that is not TOML is reported with the error of its one read on every line that needs it: the client,
  gh, its logins, the review mode and the instructions corpus. gh is not run.

</details>

## Create the operational corpus: `brigade init`

```
brigade init
brigade init --json
```

It creates the operational corpus in `$XDG_CONFIG_HOME/brigade/`, `~/.config/brigade/` by default:

- a git repository holding `_schema.awawa` and a `.gitignore`, committed with your git identity;
- `config.toml`, the machine configuration, every key commented out and never committed.

> **Watch out:** `brigade init` needs `user.name` and `user.email` set in git.

<details><summary>Running <code>brigade init</code> again</summary>

Run again, it rewrites nothing: a file that differs from the shipped one is left as it is and reported as a warning.

</details>
