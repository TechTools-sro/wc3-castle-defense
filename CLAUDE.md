# TechTools Castle Defence — AI context

An 8-player co-op hero lane-defense map for **WarCraft III TFT 1.27b**, generated 100% from code
(terrain, walls, objects, JASS, art). There is no World Editor project: **never hand-edit a `.w3x`**.
Change the generator, rebuild.

Start here, then read only what the task needs:

| Doc | Read it when |
|---|---|
| `docs/gameplay.md` | Changing rules, balance, shops, waves, commands, UI text (exact numbers + where each lives) |
| `docs/balance.md` | Changing monster strength, scaling or the economy: the rule, what was measured, what was not |
| `docs/architecture.md` | Touching code: build pipeline, file map, JASS function map, object-ID registry, data flow |
| `docs/wc3-127-gotchas.md` | Anything engine/format related. **Every entry was hit for real — read before "fixing" something odd** |
| `docs/test-env.md` | Running the map in the real game: the hidden test environment, its outputs, limits and rollback |
| `docs/techtools-warcraft-tool.md` | The website around this map: VPN, catalogue, accounts, voice, messages, what lives where |
| `README.md` | Human overview + build/install |

## Build, install, test

```bash
python3 build.py            # dist/TechToolsCastleDefence.w3x + pjass + base-id check + installs into the game
python3 build.py --test     # dist/TechToolsCastleDefence_TEST.w3x (8 s select, revealed map, scripted self-test)
tools/test_env.py run       # builds the TEST map, runs the full self-test hidden (safe while he plays); exit 0 = clean. docs/test-env.md
tools/balance_matrix.py     # monsters and bosses by wave, no game
tools/layout_audit.py       # lanes, stages, biggest army, walls and rooms on paper, with a picture
tools/xhs_port.py check     # gen/xhs_data.py against the local X Hero Siege 3.28 (never copied into the repo)
tools/balance_probe.py run LABEL --set fight   # real fights, hidden, played by a bot. docs/balance.md
```

- **Test results file:** the TEST build writes one `PASS ...` / `FAIL ...` line per check (`TestCheck` / `TestLog`,
  flushed by `TestFlush` through the Preload writer) to `CustomMapData/TestResults/cd_test.txt` of the game that runs it.
  `tools/test_env.py run` copies it to `~/games/wc3-test-env/evidence/<run-id>/cd_test.txt`, with `result.json`, screenshots and logs; read it with
  `grep -o 'Preload( "[^"]*" )' …`. The full run (both rounds, 13 real selections, formations, edge cases + stress + final boss + victory) takes about 10 min; the runner closes the game on the `SELFTEST DONE` line.
  ⚠️ No results and a frozen clock in the screenshots = the game paused or hung, not a map bug: the runner fails such a run.
  Test champions belong to the empty slot player 2 (a shop sells to the player's closest inventory unit). ⚠️ Jiří: **every feature must
  be verified in-game** — add a `TestCheck` for it in `TestStep` (round 0 = shop/champion checks, round 1 = lanes/gates).

- The game lives in `/home/novakj/games/warcraft3` (`WC3_DIR`); the map installs to `Maps/CustomMaps/`.
  The TEST map goes only into a private copy of the game under `~/games/wc3-test-env/`, never into his game.
- A build is "done" only after: pjass passes, `check_script_data()`, `check_object_bases()` and `check_icons()` pass (all run inside
  `build.py`; add every new `InitData` block to `REQUIRED_SCRIPT_DATA`),
  and — whenever object data or game logic changed — `tools/test_env.py run` with exit 0.
- Installing is safe while he plays ONLY because `build.py` replaces the map atomically (temp file + rename).
  Never copy a map over the installed one any other way (in-place overwrite crashed his game).
- ⚠️ **Jiří's rule: close your own test game yourself the moment the test is over.** `tools/test_env.py` does it on every ending; `tools/test_env.py status` shows what runs.
- ⚠️ **Never touch the owner's running game.** Test only with `tools/test_env.py`: own Wine prefix, own copy of the game, hidden display, no sound. It works while he plays, and never targets his game. Never open a test window on his desktop, and never use `pkill`/`killall` or a pattern on `war3` or `wine`.
- In-game tests: a dialog pauses single-player.
- Crash triage: the runner copies new crash files to `evidence/<run-id>/crash/` (his own: `~/.wine/drive_c/users/novakj/AppData/Local/Temp/BlizzardError/<date>/`). `Crash.txt` only says
  ACCESS_VIOLATION — bisect by building variants (drop one object group / one script feature at a time).

## Versions

- `MAP_VERSION` in `build.py` (now **v4.3**) is in the map name, the file name (`TechToolsCastleDefence_v4.3.w3x`) and
  the catalogue title. ⚠️ **Jiří's rule: every feature = a new version (1.2, 1.3, …) AND an upload to the
  catalogue** (LAN players must have the identical file). Bump, build, commit, upload, verify the download's
  SHA-256, record the new entry below + in `CHANGELOG.md`. Install removes older `TechToolsCastleDefence*.w3x`.

## Published

- ⚠️ **The repo is PUBLIC:** https://github.com/TechTools-sro/wc3-castle-defense (Jiří's choice, 2026-11-01). Never commit
  secrets, credentials or the game's own files (`ref/`, `dist/` stay ignored). The hidden dev-cheat names in `build.py` are public.

- Catalogue (uploaded as `brainbot`): newest first — **v4.3 = https://techtools.cz/tools/warcraft3/#map/80** (current),
  v4.2 = #79, v4.1 = #78, v4.0 = #77, v3.9 = #76, v3.8 = #75, v3.7 = #74, v3.6 = #73, v3.5 = #72, v3.4 = #71, v3.3 = #35 (v3.0–v3.2 were never uploaded), v2.9 = #34, v2.8 = #33, v2.7 = #32, v2.6 = #31, v2.5 = #30, v2.4 = #29, v2.3 = #28, v2.2 = #27, v2.1 = #26, v2.0 = #25, v1.9 = #24, v1.8 = #23, v1.7 = #22, v1.6 = #21, v1.5 = #20, v1.4 = #19, v1.3 = #18,
  v1.2 = #17 and v1.1 = #16 (both have the broken Bank / upgrades), unversioned = #3 (stale; only an admin can
  delete old entries).
  Upload = `POST /warcraft3-api/maps` (multipart `file`, `title`, `players`, `description`, `doc=@docs/map-catalog.md`)
  with a `/shared-auth-api/login` session. Since techtools-4 `53552315` the catalogue groups versions: an upload with
  the same title (minus the trailing version, e.g. "TechTools Castle Defence v1.6") joins this map as a new version
  (only its uploaders/admins can add versions); the card shows the newest, the detail page lists all versions.
  The uploader can replace the doc: `PUT /warcraft3-api/maps/:id/doc`. Keep `docs/map-catalog.md` current.

## The owner's design rules (Jiří — binding)

- **Simple, fast UX.** No walking to things, instant effects, no queues/crafting bars, no confusing items.
- **Short text only.** Messages, tooltips, help: one line, colour-coded, no prose. He replies "short responses only".
- WarCraft III colours mixed with TechTools blue; gold `|cffffcc00` = names/hotkeys, light blue `|cff4fc3ff`
  = levels/commands, orange `|cffff8c00` = next-price hints, green = bonuses.
- Fixed positions: shop buttons never move (`ubpx/ubpy` on every item).
- Keep the map small (~200 KiB was the guideline; v4.3 is 474 KiB: 12 champions' data, and 111 KiB for the native table `ability_slk_doom_fix` needs): low-res art is fine.
- Never drift back to base-building or complexity (v1 was rejected as "too complex, too big").
- Spells on Q W E R, a fifth skill on T, innate D, level 20 F. Commands: `-help`, `-zoom N`, `-cam`; Space = jump to hero, Esc = follow toggle.

## Conventions

- Balance/timing constants: `build.py` (timings), `gen/objects.py` (units, items, shop kinds, prices),
  `gen/layout.py` (all geometry, on the 128 grid). JASS reads them through generated globals (`InitData`).
- `gen/castle_logic.j` is hand-written vanilla JASS: define a function **before** its first use; never name
  a function like a common.j native (`RestartGame` broke the build). Line breaks in script strings = `\n`.
- New custom object → real base of the **same kind**; give it a fresh 4-char id (registry in
  `docs/architecture.md`); add `ubpx/ubpy` for anything sold in a shop.
- Git: trunk-based on `main`, history in `CHANGELOG.md`. Remote `origin` is the public GitHub repo (§ Published): push finished work there.
  `dist/`, `ref/` (Blizzard data, never commit), `tools/pjass-src/` are ignored.
- ⚠️ **Docs are part of every change** (Jiří: "keep the .md files up to date with all important details"). In the
  same change as the code: `docs/gameplay.md` (rules + numbers + where they live), `docs/architecture.md` (new
  functions, files, object ids, data model), `docs/wc3-127-gotchas.md` (any new engine trap),
  `docs/map-catalog.md` (player-facing guide, also the catalogue doc), `CHANGELOG.md` (dated entry: what / why /
  verified or NOT verified). Before finishing, diff the function list of `gen/castle_logic.j` against the JASS
  map in `docs/architecture.md`.
