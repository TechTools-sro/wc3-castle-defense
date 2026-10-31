# Changelog

## 2026-10-31 (late) — game clock

- Scoreboard title now starts with the game time (`m:ss`, `h:mm:ss` after an hour), counted from the end of champion
  select and frozen at the end of the round; the end dialog says "VICTORY in 23:45!" / "...fallen after 23:45!".
  `TimeText` + `gGameTime` in `gen/castle_logic.j`. Verified: pjass + build; not seen in-game yet.

## 2026-10-31 (evening) — docs kept in sync with the code

- `docs/architecture.md`: JASS function map rebuilt from `gen/castle_logic.j` (11 newer functions were missing —
  `LaneStage`, `WaveGold`, `ShoppingTime`, `ReleaseWaveUnit`, `CastleShockwave`, `OnTowerDestroyed`,
  `ProtectorTick`, `IsDev`/`DevArg`/`OnDevChat`, `RemoveEnumItemCB` — and the removed `AddWaveBonuses` was still
  listed). Verified by diffing the function names in code vs doc: none missing now.
- `CLAUDE.md`: docs-with-every-change rule now names all five docs and the function-list check.

## 2026-10-31 — v3 "TechTools Castle Defence": first commit of the whole generator

**What.** An 8-player co-op hero lane-defense map for WarCraft III TFT 1.27b, generated entirely from Python
(terrain, walls, pathing, object data, JASS, art) — no World Editor. Built in one day through Jiří's rapid
feedback; v1 (big melee-base castle defense) was rejected as too complex and replaced.

**Where / features.** `build.py` (pipeline, timings, constants), `gen/layout.py` (96×96 geometry incl. the secret
grove and the NE Dark Gate lane), `gen/objects.py` (units, items, shop kinds, premium items, bank, castle upgrades,
wave rosters, hero edits), `gen/castle_logic.j` (all game logic), `gen/splash.py` + `gen/icons.py` (art),
`gen/hotkeys.py` (QWER). Gameplay spec with exact numbers: `docs/gameplay.md`; code map + object-ID registry:
`docs/architecture.md`; engine traps: `docs/wc3-127-gotchas.md`; AI entry point: `CLAUDE.md`.
Main features: champion select without walking; one lane + tower + Nexus + boss per player; stage-based
standardized waves (front 4 + wave, back wave/2); Protector + instant wave on tower kill; shared Dark Gate lane;
circle stat shop with green bonuses and fixed slots; castle shop (trees); premium armory; bank income; trees per
cleared wave; 2-min shopping breaks; unlimited hero level + Attributes skill; air attack for all heroes;
scoreboard; `-help`, `-zoom`, `-cam`, Space; hidden dev cheats for `DEV_NAMES`.

**Why the notable fixes.** Crash after loading = a custom item based on an ability id → `check_object_bases()` now
fails the build. Green icons = BLP writer put the first mip at 1184 instead of 1180. A running game crashed
("Not enough memory, SFile.cpp 898") because the installer overwrote the open map in place → install is now
temp file + atomic rename. Charmed wave units blocked the wave → `ReleaseWaveUnit`.

**Verified.** Every build: pjass parse OK, base-id check OK, `tools/verify_map.py` re-parse + top-down render
(Dark Gate and enlarged grove checked visually). In-game (Wine, `tools/run_test.sh`): load without crash, circle
shop with 8 items and purchases applied (before the green-bonus/castle-shop changes). Jiří played many rounds
and reported the bugs fixed above. Published to the TechTools catalogue as map #3 (download SHA-256 matched the
build, preview 200).

**Not verified in-game** (his game was running): the castle shop after the switch to the `Aneu`+`Aall` buyer
abilities, stage waves, Protector, Dark Gate, bank/trees, unlimited levels + Attributes, air attack, dev cheats,
the fixed BLP icons, and the big "Select a Champion" text position.
