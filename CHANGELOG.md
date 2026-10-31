# Changelog

## v1.3 — 2026-10-31 (late): Long Reach; the real cause of the Bank / upgrade bugs

- **Uploaded as catalogue map #18** untested, at Jiří's choice (HTTP 201, download SHA-256 `464065fb…` matches).

- **Root cause found:** the Level 3 refactor (`ae99bb3`) replaced a region of `build.py` that also held the
  `InitData` lines for the Bank item, income step, premium items, dev names, shop-break pings and Attributes. The map
  built and ran, but `gBankItem` / `gPremItem` were 0, so Bank buys and premium upgrades did nothing (v1.1, v1.2 are
  affected). Lines restored; new `check_script_data()` fails the build when a required data block is missing.
- **Long Reach** (Premium Armory, key Z, 1500 gold): +150 attack range per buy, max 5× (+750), so melee champions hit
  from a distance; instant via the custom upgrade `Rcrg` (new `war3map.w3q`), heroes list it under "upgrades used".
- The `--test` map buys Income, Long Reach and a premium item twice remotely and prints `income=`, `reach=` and the
  Lv 2 item slot. Verified: pjass + data check + build; in-game test pending.

## v1.2 — 2026-10-31 (late): Bank income bought remotely was never counted; income on the clock; item upgrades

- **Uploaded as catalogue map #17** (HTTP 201, download SHA-256 `9501a23e…` matches the build).

- Attributes hero skill (learnable from level 11): **+10** Strength/Agility/Intelligence per level (was +3), also the
  automatic gain above level 110.
- Premium upgrades did not work (Jiří: "it buys a 2nd item instead of upgrading"): buying a permanent item from a
  neutral shop fires no "picked up" event, so `TryUpgradePremium` never ran. `OnItemSold` now calls it directly.

- Since the grove shops sell remotely, a bought item lands **on the ground at the shop** (buyer far away), so the
  pickup handler never saw Bank purchases (income stayed +0) and remote premium items stayed in the grove. New
  `OnItemSold` (`EVENT_PLAYER_UNIT_SELL_ITEM`, fires for neutral shops) counts Bank buys and hands every other
  remote purchase to the buyer. The `--test` map now buys Income remotely and prints `income=` at t=40.
  Verified: pjass + build; the in-game test is pending (his game was running).

## 2026-10-31 (late) — income paid on the game clock

- Bank income was paid by its own 60 s timer started at map load, so it never landed on the clock's full minutes
  (Jiří: "8:00 ticked, no gold"). `IncomeTick` now runs from `OnTick` whenever the game clock hits a full minute
  (1:00, 2:00, …); the separate timer is gone. Verified: pjass + build; not seen in-game yet.

## v1.1 — 2026-10-31 (late): versioned build, uploaded for LAN play

- `MAP_VERSION = "1.1"` is now in the map name (`TechTools Castle Defence v1.1`, version in light blue), the file name
  (`TechToolsCastleDefence_v1.1.w3x`) and the catalogue title; install removes older `TechToolsCastleDefence*.w3x`.
- Uploaded to the TechTools catalogue as **map #16** (HTTP 201; the download's SHA-256 `cf1ba302…` matches the
  build; preview 200) so Jiří's friend can download the identical file. Entry #3 (pre-versioning) is stale.

## 2026-10-31 (late) — coloured map name

- The map name in the game's map list, lobby and loading screen is now coloured: `TechTools` in TechTools blue,
  `Castle Defence` in WarCraft gold (`MAP_NAME_COLORED` in `build.py`: w3i name, loading-screen title,
  `SetMapName`, MPQ header). Verified: build; not seen in-game yet.

## 2026-10-31 (late) — grove shops sell remotely

- The original `Aneu` (neutral shop buyer selection, used by the Premium Armory, Bank and Apothecary) now has a
  20 000 radius: select a grove shop and buy with your champion anywhere on the map. Verified: build; not tried
  in-game yet.

## 2026-10-31 (late) — Levels 4 and 5, gate bosses, standardized wave units

- **Levels 4 (Shadow Gate, SW) and 5 (Inferno Gate, far SW chamber behind the L4 base)**; all gate levels now come
  from one table `GATE_LEVELS` (`gen/objects.py`) + `GATE_GEOMETRY` (`gen/layout.py`) and scale up per level
  (tower 40k→130k, Nexus 80k→400k with attacks 650→1600, wave bonus HP +300→+2000 / dmg →+50, gold ×2→×5,
  Nexus/boss gold 500→3000). Gate code generalized to lanes 8–11.
- **Gate bosses:** a gate Nexus that falls raises a boss (×3/×5/×8/×12 lane-boss HP, spells copied from a lane boss);
  the level is cleared when it dies (`OnGateBossSlain`); waves continue from the ruins meanwhile; victory needs all
  four levels cleared. **Gate Protectors** get the level's bonus HP/damage, 1.8× size and colour.
- **Standardized wave units:** melee 200 HP / 30 dmg, ranged 120 HP / 60 dmg (Jiri's numbers), ×2 / ×3 by stage;
  spawned as custom copies `q<arm><stage><m|r>` of each faction's stage models.
  Verified: pjass + base-id check + build; the self-test now walks through all gate levels and bosses, but it was
  not run (his game was running).

## 2026-10-31 (late) — income on the scoreboard

- New scoreboard column **Income** (`+N`, bank gold per minute) after Deaths (`CreateBoard` / `UpdateBoard`).
  Verified: pjass + build; not seen in-game yet.

## 2026-10-31 (late) — economy: smaller income, kill gold = wave

- Bank: 1 tree now buys **+10 gold/min** (was +100), `INCOME_STEP`.
- Minion kill gold = **wave number** (×2 Level 2, ×3 Level 3) paid by `MinionBounty` (replaces `SharedBounty`);
  all wave unit types get built-in bounty 0 (`NO_BOUNTY`, `wave_unit_types()`), towers/Nexus/bosses/Protectors keep
  theirs. Verified: pjass + build; not tried in-game yet.

## 2026-10-31 (late) — in-game self-test of the current build

Ran the `--test` map in Wine (`tools/run_test.sh`, 115 s, **no crash**, no new BlizzardError folder). Seen on the
screenshots: champion bought from the Hall of Mercenaries; circle buys applied (+100 Health) and **all 8 circle
icons render** (the Str/Agi/Int BLP fix works); restart → champion select; first wave cleared → level 2 and
"+100 gold +1 tree"; tower kill → Protector + instant wave; **castle buy through the castle shop accepted**
(neutral order) → "+1000 castle max HP", title "Castle 9000 / 9000"; Nexus kill → boss + **LEVEL 2** opens;
Dark Spire → Protector; Dark Citadel destroyed (+500) → **LEVEL 3** opens; Frozen Spire / Frozen Throne
destroyed (+1000); victory dialog "VICTORY in 0:52!" (game clock). Not covered by the script: a human clicking
the castle shop, premium merges, bank purchase, dev cheats, -break/-wave, unlimited levels, melee vs flyers.

## 2026-10-31 (late) — Level 3, bigger map, stronger towers

- **Level 3 — the Frozen Gate (NW):** second shared lane, opens when the Dark Citadel (Level 2) falls. Corridor
  around the Hall of Champions (`LEVEL3_RECTS`), Frozen Spire 60 000 HP / ~900 dmg, Frozen Throne 150 000 HP with a
  900 + 4d30 missile, ice-blue waves (+500 HP, +damage), +(30 + wave) gold per kill, +1000 gold when it falls;
  victory now also needs the Frozen Throne. Gate code generalized from one shared lane to two:
  `LaneArm`, `OpenGateLane(L)`, `OnGateNexusDestroyed(L)`, `gGateState[L]` (replaces `gSharedState`).
- **Map 96×96 → 112×112:** player lanes 1024 longer (`LANE_END` 4992, base rooms 4992–5888); tower at v 3600
  (1776 from the Champion's Circle, was 1076), Nexus 5440, waypoints re-spaced.
- **Towers:** lane tower 25 000 HP and ~500 damage (was 1800 / ~96); Dark Spire 40 000 / ~700.
  Verified: pjass + base-id check + build + top-down render (both gate corridors, longer lanes);
  not tried in-game yet (his game was running).

## 2026-10-31 (late) — upgradable premium items

- Premium items level up to Lv 5: picking up a shop (Lv 1) premium item while holding the same item merges both
  into the next level (`TryUpgradePremium`); at Lv 5 a new buy is refunded (1000 gold). Each level is its own
  item (`Iu<i><L>`) + ability (`Xu<i><L>`) with stronger values (table in `docs/gameplay.md`), generated from
  `PREMIUM_DEF` in `gen/objects.py`. Verified: pjass + build (32 level items + 8 shop items in w3t);
  not tried in-game yet.

## 2026-10-31 (late) — Nexus fights back, tower moved forward

- Every lane Nexus: 30 000 HP (10× the old 3000), armor 10, and a **huge attack** (450 + 4d20 chaos missile every
  2.5 s, range 700, air too). Dark Citadel: 80 000 HP, armor 15, 650 + 4d25. `nexus_attack()` in `gen/objects.py`.
- Lane towers moved from right in front of the Nexus (v 4096) to mid-lane (v 2900), Dark Spire likewise (y 2900), so
  tower and Nexus ranges never overlap: tower → stronger waves → Nexus, one at a time. Tower spawns at 2660,
  lane waypoints re-spaced so point 1 lies below the spawn.
  Verified: pjass + build + top-down render; not tried in-game yet.

## 2026-10-31 (late) — pace settings

- New chat commands for any player: `-break N` (shopping break 5–300 s, default 120) and `-wave N` (gap between
  waves 1–60 s, default 10); no number shows the current values; changes are announced to everyone and shorten a
  running countdown at once. Listed in `-help`. `OnConfigChat` in `gen/castle_logic.j`.
  Verified: pjass + build; not tried in-game yet.

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
