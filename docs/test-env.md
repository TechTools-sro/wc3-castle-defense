# Hidden test environment

Test the map in the real game while the owner plays his own game on the same machine.

```bash
tools/test_env.py run
```

This builds the TEST map (`--test --no-install`), runs the whole self-test on a hidden display, closes the game and
prints a verdict. It takes about 3 minutes. Exit 0 means a fresh `SELFTEST DONE`, no `FAIL` line, no new crash evidence, nothing
left running, and the game held no personal path or device. If no other client was active during the run, personal data must also show zero change.
While he plays, his game changes those files itself: the diff is recorded in `personal-diff.json` and does not decide the exit code.

| Exit | Verdict | Meaning |
|---|---|---|
| 0 | `PASS` | all of the above |
| 1 | `FAILED_CHECKS` | the test ended with `FAIL` lines |
| 2 | `REFUSED` | a safety check said no, or the build failed |
| 3 | `TIMEOUT`, `STALLED` | no `SELFTEST DONE` in time, or no new result for 300 s (paused or hung game) |
| 4 | `GAME_EXITED`, `NO_GAME`, `NO_RESULT`, `STALE_RESULT` | the game ended early, never started, or the results are missing or old |
| 5 | `CRASH` | a new or changed file in the crash folders of the slot |
| 6 | `ISOLATION_VIOLATION`, `CLEANUP_FAILED` | the game held a personal path, an audio or GPU device, the prefix audit failed, personal data changed with no other client active, or something stayed running |
| 130 | `INTERRUPTED` | stopped by a signal, the slot was cleaned |

Other commands: `tools/test_env.py status`, `cleanup [--slot a] [--force]`, `concurrency`, `verify-branches`.
Options of `run`: `--slot a|b` (default: the first free one), `--map FILE`, `--timeout` (default 1200 s), `--stall`.

## Where everything is

`~/games/wc3-test-env/` (`CD_TEST_ROOT`), outside this repo and outside the game. Nothing there is committed.

| Path | What |
|---|---|
| `slots/<a,b>/prefix/` | own Wine prefix, a real directory |
| `slots/<a,b>/prefix/drive_c/war3/` | own copy of the game: real files from an allow-list (`GAME_FILES` in the tool), no maps, saves, replays or profiles |
| `slots/<a,b>/prefix/drive_c/war3/CustomMapData/TestResults/cd_test.txt` | results of the current run |
| `slots/<a,b>/{home,runtime,tmp,run}/` | own `HOME`, `XDG_RUNTIME_DIR`, temp, cookie and state |
| `evidence/<run-id>/` | what one run proved, kept until someone deletes it |

A slot takes about 2 GB and is prepared once (about 30 s). Later runs reuse it and wipe `CustomMapData`, `Maps`, `replay`, `save`.

In `evidence/<run-id>/`: `result.json` (verdict, identities of game, wineserver and Xvfb, map and results hash), `run.log`,
`progress.jsonl` (every new result line with time, CPU and memory), `status.json`, `cd_test.txt`, `TechToolsCastleDefence_TEST.w3x`
(the exact map, read-only), `wine.log`, `xvfb.log`, `screens/`, `process-audit*.json`, `prefix-audit*.json`, `war3-env.json`,
`foreign-*.json`, `personal-diff.json`, `cleanup*.json`.

## How it is separated

| Shared thing | How it is kept apart |
|---|---|
| "Warcraft III is already running" | The text is in `Warcraft III.exe`, and a second `war3.exe` in one prefix joins the running game. Named objects live in the wineserver, and each prefix has its own |
| The owner's desktop | Own Xvfb (`-displayfd` picks a free number, `-nolisten tcp`, private cookie). The tool refuses `:0` and the host's display. Screenshots come only from that display. No clicks, no focus, no window manager, no `xdotool` |
| Single-player pause | The game runs in a Wine virtual desktop on that Xvfb, nothing ever takes focus from it. A stalled result stream fails the run |
| GPU | Software Vulkan (lavapipe) through the game's own DXVK. `VK_DRIVER_FILES` hides the NVIDIA driver, and the run fails if the game opens `/dev/nvidia*` or `/dev/dri` |
| Audio | `Audio=""` in `HKCU\Software\Wine\Drivers`, game sound settings off, no audio server in the environment. The run fails on `/dev/snd` or an audio server socket |
| Personal files | Private `HOME`, so a fresh prefix has real `Documents` and `Desktop` folders. Drive `z:` is deleted. Both are audited before and after every run |
| Registry | A short seed written by the tool (`REG_SEED`), nothing copied from `~/.wine` |
| Environment | Every process gets a complete environment built from nothing, so an inherited `WINE*`, `DISPLAY`, `WAYLAND_DISPLAY` or DBus address cannot redirect it |
| CPU | 4 logical CPUs per slot, `nice 10`, idle I/O class, `LP_NUM_THREADS=2`. In use: about 1 CPU and 900 MB |
| LAN | Not sandboxed. `netgameport` is set to 6199 in the slot, and `-loadfile` is a single-player game |

⚠️ **A prefix is not a filesystem sandbox.** A Windows program can still reach Unix paths. Deleting `z:` and the private `HOME` remove the normal routes, the
audits detect the rest. Do not use this environment for untrusted maps.

## Cleanup

Identity is the exact environment marker (`CD_TEST_SLOT=<slot>` or `WINEPREFIX=<prefix>`) plus PID and start time, re-checked through a pidfd
right before a signal. Never a process name or a pattern. The owner's game has neither marker, so no code path can hit it.

1. `wineserver -k` of that prefix (the tool checks the prefix first: never `~/.wine`, never a symlink).
2. SIGTERM, then SIGKILL, to whatever of the slot is still alive.
3. The lock and socket of the recorded private display, if Xvfb left them.

It runs on success, failure, timeout and signals. A watchdog process keeps the slot lock and cleans the slot when the runner dies by `kill -9`.
The next run also cleans leftovers before it starts.

The verdict is decided after the game has stopped (`final_gate`): the results file must be newer than the start of this game, complete and
clean, and no file in the slot's crash folders may be new or changed (size, mtime and hash).

Builds take a lock and the run keeps its own read-only copy of the map, so parallel runs cannot test a half-written `dist/` file.

## What was verified

pc1, 2026-11-01, no client of the owner running. Evidence is under `~/games/wc3-test-env/evidence/`. `tools/test_env.py concurrency` and `verify-branches` repeat the proof.

| Code (SHA-256 of `tools/test_env.py`) | Check | Result | Evidence |
|---|---|---|---|
| `185ec3134b5d…` | every error path (`verify-branches`), with real games where a game is involved | 37 passed, 0 failed | `branches-20261101-143714-2b87` |
| `185ec3134b5d…` | two hidden clients (`concurrency`) | 30 passed, 0 failed; both full runs 60 PASS, 0 FAIL | `concurrency-20261101-144500-e72d` |
| `f219a3785a6a…` (committed) | `concurrency` again | 30 passed, 0 failed; both full runs 60 PASS, 0 FAIL | `concurrency-20261101-145144-06f3` |
| `f219a3785a6a…` (committed) | choice of the concurrency branch, 4 cases, no game: a targeted test, not an engine run | all correct | |

`verify-branches` was not repeated on the committed code: the only change after `185ec3134b5d…` is the choice of the concurrency branch, its log text and four checks of it in `verify-branches`. Those four checks have only run in the targeted test.

What the concurrency proof shows: client B ended by timeout, by interrupt and by `kill -9` of its runner while A played, and A stayed the same process and went on. A's normal end did not disturb B, whose results grew from 17 to 41 PASS after A was gone. Different game and wineserver processes, server folders and displays at the same moment. No own process left, no window on the owner's display, and zero change in the real game tree and `~/.wine` registry.

**Limit:** when the owner's client is not running, concurrency means two hidden clients on separate displays and prefixes. It is a simulation, not a
session played by him. It does not exercise his display, GPU, audio or launcher, or how his game feels beside a test. Only a run while he plays can prove that. In that case
the tool observes his client read-only and records whether it survived. Only a running `war3*` process selects that branch: a lone wineserver is reported as another Wine process, and the proof still uses two hidden clients.

Software rendering tests the map's logic, not how it looks on a real GPU.

While a finished client is held open for the concurrency proof, it sits on the victory dialog, which pauses the game. Then a live process and CPU activity
are the only signal, not the game clock. Progress of the game is proven by the `PASS` lines during the map and by the full runs that end the proof.

## Rollback

The old runner opened a window on the owner's desktop and killed by a process-name pattern, so it is no longer in the tree.

```bash
git show 9cba731:tools/run_test.sh > tools/run_test.sh && chmod +x tools/run_test.sh
```

To remove the environment: stop it with `tools/test_env.py cleanup`, then delete `~/games/wc3-test-env`. It touches nothing else.
