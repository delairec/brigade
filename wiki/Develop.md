How to work on brigade itself: the local checks, what the continuous integration runs, how the tests replay awawa,
and how this wiki is written and published.

## Local checks

```
python3 -m unittest                            # the tests: tests/cli runs brigade as a subprocess, tests/guards
                                               # checks the import graph and the environment reads
awawa fmt --check . && awawa lint --strict .   # the checks of the corpus
ruff check . && ruff format --check .          # the lint and the format, where ruff is installed
```

> **Watch out:** the ruff pinned in `requirements-ci.txt` gives the verdict that counts; install that version to check
> locally.

## Continuous integration

The CI runs the tests in parallel under pytest-xdist, then the zipapp build, on Python 3.11 and on the latest Python
release. On every pull request it also runs:

| Tool | What it does |
|---|---|
| ruff, configured by `ruff.toml` | lints and checks the format |
| semgrep | scans the repository with semgrep under its Python and security-audit rule packs |
| vulture | reports the dead code of `brigade/` and `tests/` with vulture, run in the CI only |
| coverage | measures the line and branch coverage of `brigade/` by the unit tests of `tests/unit` alone with coverage.py, in a job of its own on Python 3.11, configured by `.coveragerc`: a report read in the job log only, the job failing below the `fail_under` threshold of `.coveragerc`, never lowered |
| zizmor | audits its workflows with zizmor |

pytest, pytest-xdist, ruff, semgrep, vulture, coverage and zizmor are pinned in `requirements-ci.txt`, which
dependabot keeps current. pytest runs the `unittest` cases as they are, and `python3 -m unittest` stays the local
command.

## The awawa recordings

The tests that need awawa run against the real awawa where it is on PATH, and otherwise against a fake that replays
the recordings of `tests/awawa/recordings/`. A recording is made, or renewed after a bump of awawa or a change of a
call, from the real binary:

```
rm -r tests/awawa/recordings && AWAWA_RECORD=1 python3 -m unittest   # awawa on PATH
```

> **Watch out:** a call with no recording fails its test, naming its arguments.

<details><summary>What a recording holds, and how it is checked</summary>

- A recording holds what the real awawa printed, its exit code and the files it rewrote, for the same arguments on the
  same input files.
- Each recording names the awawa version it was made with and the order its run ids sorted in, which the replay keeps
  for two runs of the same second.
- The CI installs no awawa, so its tests run on the recordings and none is skipped.
- Where awawa is on PATH, `tests/awawa/test_recordings.py` replays every recording against it and fails on a
  difference, naming the recording, its version and the version `awawa --version` prints.

</details>

## The wiki

The documentation is the pages of `wiki/`, one page per subject, changed by a branch and a pull request like any other
file.

- `Home.md` names every page with the question it answers, and `_Sidebar.md` groups them.
- A page opens with one short paragraph saying what it answers, then gives the essentials; its common pitfalls are
  quotes opened by **Watch out:**, and its edge cases are folded in `<details>` blocks.
- A link to another page targets its file name, `Page-Name.md`, which the blob view of the repository resolves; a link
  to a file outside `wiki/` is an absolute `https://github.com/delairec/brigade/...` address.
- `tests/guards/test_wiki_links.py` fails on a link that names no page of `wiki/`, and on a page `Home.md` or
  `_Sidebar.md` does not link.

> **Watch out:** nothing but the workflow writes the wiki repository: a page edited on GitHub is replaced at the next
> push to `main`.

<details><summary>How the wiki is published</summary>

`.github/workflows/wiki.yml` publishes `wiki/` to the GitHub wiki, `https://github.com/delairec/brigade.wiki.git`, on
each push to `main`: it rewrites each `(Page-Name.md)` and `(Page-Name.md#anchor)` link into the `(Page-Name)` form the
wiki resolves, replaces the files of the wiki's `master` with them and pushes a commit naming the commit of `main` it
publishes, when they differ.

</details>
