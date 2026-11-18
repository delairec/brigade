Which platforms brigade runs on today, feature by feature, and why a feature breaks where it does. brigade is
developed and tested on Linux only; it supports Linux, macOS and Windows once the milestone M19 is delivered,
each checked by a CI job on that platform.

Every pull request that changes how a feature behaves on a platform updates this table in the same change.

## Support by feature

Read at `f23e9bcd`. **works**: the feature behaves as documented. **degraded**: it runs, with a fallback or a missing
check. **broken**: it fails, or gives a wrong answer.

| Feature | Linux | macOS | Windows | Cause |
|---|---|---|---|---|
| Install from a clone (`ln -s bin/brigade`) | works | works | broken | a symlink and an executable bit; Windows needs a `.cmd` shim or `py -m` |
| Zipapp (`python3 build.py`, `dist/brigade.pyz`) | works | works | degraded | the shebang `/usr/bin/env python3`; run it as `py dist/brigade.pyz` |
| Locks of the state, the ledger, the corpus and the worktrees | works | works | broken | `fcntl.flock` (`brigade/system/hold_lock.py`, `hold_lock_without_waiting.py`): the module does not exist on Windows, so brigade fails at import |
| Scheduler | works: systemd, cron or loop | degraded: cron or loop, no launchd | degraded: `brigade tick --loop` only | `brigade/adapters/schedulers/`: no launchd or Task Scheduler adapter |
| A run seen alive or dead (`run list`, the tick, `runs stop`) | works | broken | broken | the start time and boot id are read in `/proc` (`brigade/system/identify_process.py`); without `/proc` a live run reads as dead, with no error |
| `brigade runs stop` | works | degraded | broken | `/proc/<pid>/status` tells whether the run catches SIGTERM (`brigade/system/is_catching_signal.py`); the run tree is killed by `os.killpg` and `SIGKILL` (`brigade/system/stop_process_group.py`), absent on Windows |
| Waiting on a run with a signal to stop | works | works | broken | `select` on a pipe (`brigade/system/poll_until_signalled.py`) takes sockets only on Windows |
| Client and plugin executables found on `PATH` | works | works | degraded | `os.access(X_OK)` and the `brigade-<name>` naming ignore `PATHEXT` |
| `brigade doctor` | works | degraded | degraded | the linger and the user systemd instance are probed with `loginctl` and `systemctl`: warnings with no meaning off Linux |
| Dashboard (`brigade serve`) | works | works | works | the standard library HTTP server on loopback |
| Privacy check of `brigade build check` | works | works | degraded | the home paths it looks for are `/home/` and `/Users/`, not `C:\Users\` |

## Continuous integration

Every job of `.github/workflows/` runs on Ubuntu: nothing above is tested on macOS or Windows.
