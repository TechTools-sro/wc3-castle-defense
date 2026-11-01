# TechTools Castle Defence — AI context

An 8-player co-op hero lane-defense map for **WarCraft III TFT 1.27b**, generated 100% from code
(terrain, walls, objects, JASS, art). There is no World Editor project: **never hand-edit a `.w3x`**.
Change the generator, rebuild.

Start here, then read only what the task needs:

| Doc | Read it when |
|---|---|
| `docs/gameplay.md` | Changing rules, balance, shops, waves, commands, UI text (exact numbers + where each lives) |
| `docs/architecture.md` | Touching code: build pipeline, file map, JASS function map, object-ID registry, data flow |
| `docs/wc3-127-gotchas.md` | Anything engine/format related. **Every entry was hit for real — read before "fixing" something odd** |
| `README.md` | Human overview + build/install |

## Build, install, test

```bash
python3 build.py            # dist/TechToolsCastleDefence.w3x + pjass + base-id check + installs into the game
python3 build.py --test     # dist/TechToolsCastleDefence_TEST.w3x (8 s select, revealed map, scripted self-test)
tools/run_test.sh 'Maps\Test\TechToolsCastleDefence_TEST.w3x' <outdir> 40   # Wine run + screenshots
```

- The game lives in `/home/novakj/games/warcraft3` (`WC3_DIR`); the map installs to `Maps/CustomMaps/`.
  Test copies go to `Maps/Test/` — **delete that folder when done**.
- A build is "done" only after: pjass passes, `check_script_data()` and `check_object_bases()` pass (all run inside
  `build.py`; add every new `InitData` block to `REQUIRED_SCRIPT_DATA`),
  and — whenever object data or game logic changed — an in-game run without a new `BlizzardError` crash folder.
- Installing is safe while he plays ONLY because `build.py` replaces the map atomically (temp file + rename).
  Never copy a map over the installed one any other way (in-place overwrite crashed his game).
- ⚠️ **Never touch the owner's running game.** `run_test.sh` refuses if any `war3.exe` is up. If it is,
  ship the build and say plainly that it is untested in-game. Ask before asking him to close it.
- In-game tests: a dialog pauses single-player; clicking the test window (xdotool) freezes it.
- Crash triage: `~/.wine/drive_c/users/novakj/AppData/Local/Temp/BlizzardError/<date>/Crash.txt` only says
  ACCESS_VIOLATION — bisect by building variants (drop one object group / one script feature at a time).

## Versions

- `MAP_VERSION` in `build.py` (now **v1.8**) is in the map name, the file name (`TechToolsCastleDefence_v1.8.w3x`) and
  the catalogue title. ⚠️ **Jiří's rule: every feature = a new version (1.2, 1.3, …) AND an upload to the
  catalogue** (LAN players must have the identical file). Bump, build, commit, upload, verify the download's
  SHA-256, record the new entry below + in `CHANGELOG.md`. Install removes older `TechToolsCastleDefence*.w3x`.

## Published

- Catalogue (uploaded as `brainbot`): newest first — **v1.8 = https://techtools.cz/tools/warcraft3/#map/23** (current),
  v1.7 = #22, v1.6 = #21, v1.5 = #20, v1.4 = #19, v1.3 = #18,
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
- Keep the map small (~200 KiB): low-res art is fine.
- Never drift back to base-building or complexity (v1 was rejected as "too complex, too big").
- Spells on Q W E R. Commands: `-help`, `-zoom N`, `-cam`; Space = jump to hero, Esc = follow toggle.

## Conventions

- Balance/timing constants: `build.py` (timings), `gen/objects.py` (units, items, shop kinds, prices),
  `gen/layout.py` (all geometry, on the 128 grid). JASS reads them through generated globals (`InitData`).
- `gen/castle_logic.j` is hand-written vanilla JASS: define a function **before** its first use; never name
  a function like a common.j native (`RestartGame` broke the build). Line breaks in script strings = `\n`.
- New custom object → real base of the **same kind**; give it a fresh 4-char id (registry in
  `docs/architecture.md`); add `ubpx/ubpy` for anything sold in a shop.
- Git: trunk-based on `main`, history in `CHANGELOG.md`. ⚠️ **Local-only repo on pc1 — no remote, no backup.**
  `dist/`, `ref/` (Blizzard data, never commit), `tools/pjass-src/` are ignored.
- ⚠️ **Docs are part of every change** (Jiří: "keep the .md files up to date with all important details"). In the
  same change as the code: `docs/gameplay.md` (rules + numbers + where they live), `docs/architecture.md` (new
  functions, files, object ids, data model), `docs/wc3-127-gotchas.md` (any new engine trap),
  `docs/map-catalog.md` (player-facing guide, also the catalogue doc), `CHANGELOG.md` (dated entry: what / why /
  verified or NOT verified). Before finishing, diff the function list of `gen/castle_logic.j` against the JASS
  map in `docs/architecture.md`.
