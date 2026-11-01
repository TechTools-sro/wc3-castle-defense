# Changelog

## v2.4 — 2026-11-01: Shadow Crown icon

- **Uploaded as catalogue map #29** (HTTP 201, download SHA-256 `054c3457…` matches).

- Jiří (screenshot): the Shadow Crown (Level 4 EPIC drop) showed a green square. Its icon `BTNCrownOfKings` does not
  exist in 1.27 → now `BTNHoodOfCunning` (`EPIC_ITEMS`). New `check_icons()` in `build.py` fails the build when any
  unit/item icon is missing from the game MPQs and the map (verified: it rejects the old path, passes the new one).
  Not tried in-game.

## v2.3 — 2026-11-01: tower HP ÷ 6

- **Uploaded as catalogue map #28** (HTTP 201, download SHA-256 `870ae576…` matches).

- Jiří: "nerf hp of the towers at least 6x". Lane tower 25 000 → 4 000 HP (`TURRET_HP`), gate towers L2–L5
  40 000 / 60 000 / 90 000 / 130 000 → 6 500 / 10 000 / 15 000 / 21 000 (`GATE_LEVELS[*]["tower"]`). Damage unchanged.
  Verified: pjass + build; not tried in-game.

## v2.2 — 2026-11-01: Nexus HP ÷ 4 again

- **Uploaded as catalogue map #27** (HTTP 201, download SHA-256 `33349f58…` matches).

- Jiří: "nerf the HP of the nexus even more, at least 4x less". Every Nexus HP ÷ 4 (`BASE_HP`, `GATE_LEVELS[*]["nexus"]`):
  lane 12 000 → 3 000; gates L2–L5 8 000 / 15 000 / 25 000 / 40 000. Attack unchanged. Verified: pjass + build; not
  tried in-game.

## v2.1 — 2026-11-01: Long Reach = one +150 buy, melee champions only

- **Uploaded as catalogue map #26** (HTTP 201, download SHA-256 `d1535369…` matches).

- Jiří: Long Reach was bugged — stacking 5 × +150 let champions (ranged ones especially) outrange the towers. Now one
  buy, +150 attack range, melee champions only (`REACH_LEVELS` = 1 in `gen/objects.py`; `TryReach` refunds a ranged
  champion via `UNIT_TYPE_MELEE_ATTACKER` and a second buy; only the `cleave` champions list `Rcrg` in `upgr`; new
  `gReachPrice` replaces the hard-coded refund). Verified: pjass + build; not tried in-game.

## v2.0 — 2026-11-01: one Hall of Champions, 6 multi-target champions

- **Uploaded as catalogue map #25** (HTTP 201, download SHA-256 `810e472d…` matches).

- Jiří: remove the champion choice across several buildings; one building with 6 champions, every one with splash
  or multi-target attacks. The 5 taverns / 24 heroes are replaced by **one tavern `tvc0`** with `CHAMPIONS` in
  `gen/objects.py`: Mountain King, Tauren Chieftain, Pit Lord (melee **cleave** 50 % within 250, new ability `Xclv`),
  Archmage, Lich (**splash** missile 100/200/300, 60 %/30 %), Far Seer (**bounce** to 4 enemies, −20 % per jump).
  The pick is no longer exclusive (6 champions, up to 8 players; stock 8); short tavern tooltips name the attack.
  `AssignHero` no longer locks a picked hero for the others; test buy uses `gHeroPool[0]`.
  Verified: pjass + build; not tried in-game.

## v1.9 — 2026-11-01: buy experience at the Champion's Circle

- **Uploaded as catalogue map #24** (HTTP 201, download SHA-256 `f234d422…` matches).

- Jiří: "add to the champions circle option to buy xp for gold". New circle kind **Experience +1 level** (row 3, key Z,
  250 gold, +10 % per buy, 40 steps; `KINDS_DEF` kind type `xp` = 2 in `gen/objects.py`, item `Ix00`–`Ix39`). Each buy
  adds exactly one level's worth of XP, `100 × (level + 1)` = the game's NeedHeroXP step, so it stays one level at any
  level (`AdvanceStatPrice`). The castle kinds moved one index up (first castle kind = 9; the test step follows).
  Verified: pjass + build; not tried in-game.

## v1.8 — 2026-11-01: premium item upgrades no longer depend on shop events

- **Uploaded as catalogue map #23** (HTTP 201, download SHA-256 `1c121554…` matches).

- Jiří: buying the same premium item still gave a 2nd copy instead of upgrading it ("so crucial bug"). The old merge
  ran only inside the shop events (`OnItemSold` / `OnItemPickup`) and still failed in play; the exact engine cause
  was not reproduced. New `MergePremium` (`gen/castle_logic.j`): two items of one family in an inventory become one at
  the summed level (Lv 1 + Lv 3 → Lv 4, capped at 5, excess refunded). It runs on buy, on pickup **and every 0.2 s for
  every champion from `GrabTick`**, so it works whatever event fires; premium purchases always go to the champion.
  Replaces `TryUpgradePremium`. Verified: pjass + build. **Not tried in-game** (Jiří chose to ship untested).

## v1.7 — 2026-11-01: potions heal % and stack

- **Uploaded as catalogue map #22** (HTTP 201, download SHA-256 `194772af…` matches).

- Jiří: the potion economy made no sense (a 150-gold potion healed a fixed 250 HP on champions with thousands of HP)
  and potions should stack in the inventory. Apothecary potions now heal a percent of max (`POTIONS` in
  `gen/objects.py`; the native amounts of `AIh1`/`AIm1`/`AIre` are zeroed, `DrinkPotion` heals on USE): Healing 50 % HP
  and Mana 50 % mana for 100 gold (10 s cooldown), Restoration 100 % HP + mana for 250 (30 s), Invulnerability 200.
  Greater Healing / Greater Mana / Lesser Clarity removed. The same potion stacks into one slot (`StackPotion`, on
  buy in `OnItemSold` and on pickup). Verified: pjass + build; not tried in-game.

## v1.6 — 2026-11-01: Nexus HP −60 %, Nexus damage ×2

- **Uploaded as catalogue map #21** (HTTP 201, download SHA-256 `56a858ac…` matches; joins the map family, 7 versions).

- Jiří: the Nexuses were far too tanky ("sniz zivoty nexusu o 60%") and should hit harder ("a zvys jim DMG").
  Every Nexus HP ×0.4, attack ×2 (`BASE_HP`, `NEXUS_DMG`, `GATE_LEVELS[*]["nexus"]` in `gen/objects.py`):
  lane 30 000 → 12 000 HP, 450+4d20 → 900+4d40; gates L2–L5 32 000 / 60 000 / 100 000 / 160 000 HP,
  1300+4d50 / 1800+4d60 / 2400+4d80 / 3200+4d100. Verified: pjass + build; not tried in-game.

## v1.5 — 2026-10-31 (late): towers 5x damage, no lifesteal on towers / Nexus

- **Uploaded as catalogue map #20** (HTTP 201, download SHA-256 `546d3b00…` matches).

- Tower damage ×5 (Jiří: "too weak"): lane tower ~2500 per hit, gate towers ~3500 / 4500 / 6000 / 8000.
- Every tower and Nexus gets the classification "Mechanical" (`NO_LIFESTEAL`; the Legion Nexus `ndmg` was the only
  base without it) — WarCraft lifesteal does not work against mechanical targets. Verified: pjass + build (17 `utyp`
  edits in w3u); lifesteal behaviour not tried in-game.

## v1.4 — 2026-10-31 (late): EPIC boss loot

- **Uploaded as catalogue map #19** (HTTP 201, download SHA-256 `052906a4…` matches).

- Every Nexus boss drops one EPIC crown instead of random items: lane boss +200 all stats, Level 2–5 bosses +400 /
  +600 / +800 / +1000 (`EPIC_ITEMS` in `gen/objects.py`, `DropEpic` in `gen/castle_logic.j`, items `Io01`–`Io05`
  based on Crown of Kings, abilities `Xo01`–`Xo05` based on `AIx1`). Verified: pjass + data check + build;
  not tried in-game.

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
