# brigade

A CLI, a timer and a local dashboard that run AI-agent waves unattended on one machine, across every
registered project. The CLI does everything mechanical; the agents only judge.

**The documentation is the wiki: <https://github.com/delairec/brigade/wiki>.** Its pages are written in
[`wiki/`](wiki/Home.md) of this repository; `Home` names every page with the question it answers.

## Install

brigade needs Python 3.11.4 or later, git and awawa. From a clone, link the entry point into a directory on your `PATH`,
then check the machine:

```
git clone https://github.com/delairec/brigade.git
mkdir -p ~/.local/bin
ln -s "$PWD/brigade/bin/brigade" ~/.local/bin/brigade
brigade doctor
```

The single-file zipapp, `brigade init` and what `brigade doctor` checks are on the wiki page
[Install](https://github.com/delairec/brigade/wiki/Install).

## Develop

```
python3 -m unittest      # the tests
```

The checks of the corpus, the lint and what the continuous integration runs are on the wiki page
[Develop](https://github.com/delairec/brigade/wiki/Develop).
