# Architecture

## Pipeline

`python3 build.py [--test] [--no-install]` does everything in one process:

1. **Terrain** `build_terrain` → `war3map.w3e` (Black Citadel tiles, abyss between lanes).
2. **Walkability** `cell_walk` from `gen/layout.py` → walls (`ITw0/ITw2` destructables, braziers/torches
   doodads) → `war3map.doo`; pathing → `war3map.wpm` (walls are abyss cells in the wpm; see gotchas).
3. **Script** `build_script` = generated `globals` + `InitData` (all constants from Python) + `gen/castle_logic.j`
   → `dist/war3map.j` → **pjass** (`tools/pjass-src/pjass` + `ref/Scripts_common.j` + `ref/Scripts_Blizzard.j`).
4. **Data check** `check_script_data`: `InitData` must contain every block in `REQUIRED_SCRIPT_DATA` (Bank, premium,
   dev names, shop pings, gates, rosters, …) — fails the build otherwise.
   **Object check** `check_object_bases`: every custom unit/item/ability must have a real base of its kind
   (checked against `ref/*.slk`) — fails the build otherwise. **Icon check** `check_icons`: every unit/item icon
   path (`uico`/`iico`) and custom ability icon (`aart`/`arar`) must exist in the game MPQs or the map.
5. **Object data**: `war3map.w3u` (units), `war3map.w3t` (items), `war3map.w3a` (abilities: original edits +
   QWER hotkeys + custom), `war3map.w3q` (upgrades: Long Reach), all via `gen/w3files.py`.
6. **Info + art + constants**: `war3mapMisc.txt` (full [Misc] gameplay constants with `MaxHeroLevel` edited), `war3map.w3i`, minimap `war3mapMap.blp` + `war3map.mmp`, `war3mapPreview.tga`
   (`splash.render_icon`), loading tiles (`splash.render` → 4 BLPs), Str/Agi/Int button icons (`gen/icons.py`).
7. **Pack** `tools/mpq.write_w3x` (StormLib via ctypes, HM3W header with max players = 8 humans) →
   `dist/*.w3x`; release builds copy into `<game>/Maps/CustomMaps/` and delete `OLD_MAP_FILES`.

## Files

| Path | What |
|---|---|
| `build.py` | Pipeline above, timings (`SELECT_TIME`, `FIRST_WAVE_DELAY`, `WAVE_INTERVAL`, `WAVE_BREAK`), map flags, player colours, globals block + `InitData` generator, `check_object_bases` |
| `gen/layout.py` | All geometry (96×96, 128-grid bounds): plaza, lanes, waypoints, bases, circles, gates, hall, grove |
| `gen/objects.py` | Factions + wave rosters, taverns/heroes, castle/soul/circle/shops/Nexus/towers/bosses, circle + castle shop kinds (`KINDS_DEF`), premium items (`PREMIUM`), original-object edits |
| `gen/castle_logic.j` | All game logic, hand-written vanilla JASS |
| `gen/hotkeys.py` | Q W E R hotkeys + tooltip retags for the 6 champions' abilities |
| `gen/splash.py` | Lobby icon (`render_icon`), loading screen (`render`, `loading_tiles`), `preview_tga` |
| `gen/icons.py` | Str/Agi/Int shop icons cut from the game's `infocard-heroattributes-*.blp` (+ DISBTN) |
| `gen/w3files.py` | Binary writers: w3e, wpm, doo, w3u/w3t, w3a/w3q (level format), paletted BLP1 |
| `tools/mpq.py` | StormLib binding: `GameData` (read game MPQs), `Archive` (read a map), `write_w3x` |
| `tools/slk.py` | SLK + profile-txt readers (used by hotkeys and the base check) |
| `tools/run_test.sh` | Wine `-loadfile` test run with screenshots; refuses if WC3 is already running |
| `tools/verify_map.py` | Re-parse a built map + render a top-down preview PNG |
| `tools/extract_ref.py`, `tools/dump_map.py` | Fill `ref/` from the game MPQs / official maps (not in git) |

## JASS map (`gen/castle_logic.j`, in file order — a function must precede its callers)

| Area | Functions |
|---|---|
| Helpers | `Msg`, `IsPlaying`, `GiveAllGold`, `SideName`, `GrantLevelTwo`, `LaneName`, `PingLane`, `LaneArm` (lane → arm: 0-7 → 0-3, 8 → 4, 9 → 5; use it instead of `L / 2`) |
| Shops | `KindNext` (per-player vs global step), `StockCircle` (player circle), `StockCastle` (castle), `CastleShockwave`, `AdvanceStatPrice` (count any circle/castle buy at once), `ApplyBought` (circle bonuses + Experience → the living champion; `gStatApplied`, `gXpPending`), `BuyIncome` + `IncomeTick` (bank, paid by `OnTick` on every full game-clock minute), `PremiumLevel` + `PremiumFamily` + `MergePremium`/`MergePremiumAll` (merge premium items, `gPremItem[i*8+L]`; also run every 0.2 s by `GrabTick`), `OnItemPickup`, `TryReach` (Long Reach), `OnItemSold` (neutral shops: counts Bank buys, hands remote purchases to the buyer — premium items always to the champion — stacks potions, merges premium items), `PotionIndex` + `StackPotion` + `DrinkPotion` (Apothecary potions: stack on buy/pickup, heal % on use), `GrabTomeEnum`/`GrabTick` (bought items on the ground → champion; premium merge sweep), `OnHeroLevel` (refill + stats past the Attributes cap) |
| Lane hint | `ShowLaneHint` (creates the circle unit, its rect, label) |
| Scoreboard | `BoardSet`, `TimeText` (m:ss), `UpdateBoard` (1 s; game time `gGameTime` counted in `OnTick`), `BoardWidth`, `CreateBoard` |
| Setup | `SetupAlliances`, `SetupDarkness`, `MakeWallInvulnerable`, `CreateKingdom`, `CreateLaneBase` |
| Waves | `LaneStage` (0 tower / 1 Nexus / 2 ruins), `SpawnWaveUnit`, `SpawnWave` (front/back/champions), `OnWaveTimer`, `NextWaveDelay` (10 s / 2-min break), `WaveGold` (paid on clear), `ShoppingTime` (break announcement + grove pings), `OnFirstWave`, `ReleaseWaveUnit` (charmed units leave the wave), `WaveUnitTick` |
| Bosses | `BossFindTarget`, `BossCast`, `BossSummon`, `BossTick` |
| Dryad skills | `OnAttacked` (Extra Spear: one flying dummy spear per level), `OnDamaged` (dummy spear hit → champion damage; Fire Spears bonus on every hit), `DmgRebuild` / `OnEnterMap` (per-unit damage registration of enemies, rebuilt past 3000), `OnHeroSkill` (Swift Throw / fire orb on learn) |
| Tick (1 s) | `OnTick`: steer waves, on a cleared wave pay gold + 1 tree and start the countdown, boss AI |
| Outcome | `ShowEndDialog`, `CheckVictory`, `OnCastleDestroyed`, `DropLoot` (unused now), `DropEpic` (boss crown by level), `AnyNexusLeft` (any lane still spawning), `OnTowerDestroyed` (Protector + instant wave), `ProtectorTick` (leash), `OnNexusDestroyed`, `OnBossSlain` |
| Gate levels | `OpenGateLane` (lanes 8–11 = Levels 2–5, each opened by the previous Nexus), `OnGateNexusDestroyed` (boss rises, next level opens), `OnGateBossSlain` (level cleared), `MinionBounty` (kill gold for every wave unit) — gate lanes reuse the lane arrays (`gTower[L]`, `gBoss[L]`, `gWpX[L*8..]`, `gStageUnit[arm*6..]`, `gGate[L]`) plus `gGateHpAbil/gGateDmgAbil/gGateTint*/gGateGold/gGateDir[L]`; state `gGateState[L]` (-1 closed, 0 open, 1 boss, 2 cleared) |
| Revive/deaths | `OnReviveTimer`, `StartRevive`, `OnUnitDeath` (kills, deaths, bounty, first-wave tracking, tower/Nexus/boss/castle), `OnPlayerLeave` |
| Camera/commands | `OnZoomChat`, `ApplyZoom`, `SetFollow`, `SpaceTick` (0.1 s quick position), `OnFollowToggle`, `OnHelpChat` |
| Dev cheats | `IsDev` (`DEV_NAMES`), `DevArg` (number after a command), `OnDevChat` (`-addmoney`, `-addwood`/`-addtree`, `-lvl`) |
| Pace settings | `OnConfigChat` (`-break N`, `-wave N` → `gWaveBreak`, `gWaveInterval`) |
| Quests | `AddQuest`, `CreateQuests` |
| Test build | `TestKillEnum`, `TestStep` (shop buys, castle buy, tower/Nexus/boss kills, Dark Gate), `TestBuyOrder`, `TestBuyHero` (only with `gTestMode`) |
| Round | `StartGame`, `HidePickTag`/`ShowPickTags`, `AssignHero`, `EndChampionSelect`, `AllChosen`, `OnUnitSold`, `SetupChampionSelect`, `RemoveEnumItemCB`, `CDRestart`, `OnEndClick` |
| Entry | `InitGame` (triggers, timers, groups; called from `main`) |

### Shop data model

- Kind `s` (0–10) = one shop button. `gStatItem[s*64 + k]` = item type for price step `k`;
  `gBonusAbil[s*64 + k]` = the hidden ability that step adds; `gKindType[s]`: 1 hero bonus, 3 castle heal,
  4 castle bonus ability, 5 castle shockwave (3 and 5 are single repeatable items, `kind_tiers`); `gKindValue/gKindName/gKindEffect[s]`.
- Price step: hero kinds `gStatNext[p*16 + s]` (per player); castle kinds `gCastleNext[s]` (global).
- What is currently in stock: `gStocked[p*16 + s]` (circle of player p), `gStocked[128 + s]` (castle).
  Only items recorded there are removed on a restock.
- A buy → item lands on the champion → PICKUP event → `AdvanceStatPrice` matches the item id against the
  buyer's current step → adds the ability (hero or castle) / heals → removes the item → restocks.

## Object-ID registry (pick new ids that collide with none of these)

| Id(s) | Kind | What |
|---|---|---|
| `hcd0` | unit (base `hcas`) | Castle of Lordaeron, allied shop |
| `ecd0` | unit | Invisible buyer ("soul") for champion select |
| `ncd3` | unit | Champion's Circle = player's own shop (`Avul,Aall,Apit,Asid`) |
| `tvc0` | unit (base `ntav`) | The Hall of Champions (the one tavern, 6 champions) |
| `shpa`, `shpb`, `shpc` | unit (base `ngme`) | Premium Armory, Apothecary, Bank (gold-mine model) |
| `ns{d}0`, `nt{d}0`, `nb{d}{k}` | unit | Nexus, tower, boss of arm d (k = player-count tier 0–2) |
| `ns40`–`ns70`, `nt40`–`nt70` | unit | Gate levels 2–5: Nexus, tower (arm 4–7, from `GATE_LEVELS`) |
| `nb41`, `nb51`, `nb61`, `nb71` | unit (boss bases of the source factions) | Gate level bosses |
| `q<arm><stage><m|r>` (e.g. `q00m`) | unit (base: the stage's model unit) | Standardized wave units (200/30 melee, 120/60 ranged, ×stage) |
| `nc{d}0` (d 0–7) | unit (base: faction champion) | Weakened wave champion (every 10th wave) |
| `Io01`–`Io05` | item (base `ckng`) | EPIC crowns dropped by Level 1–5 bosses (+200…+1000 all stats) |
| `Xo01`–`Xo05` | ability (base `AIx1`) | EPIC crown all-stats bonus |
| `Ixr1` | item (base `tst2`) | Long Reach (+150 attack range, once, melee only) — not sold since v2.6 |
| `Rcrg` | upgrade (base `Rhri`, `war3map.w3q`) | Long Reach range upgrade, 1 level, +150 (`ratr`); only the melee champions list it in `upgr` |
| `Ib01` | item (base `tst2`) | Bank: Income +10 per minute for 1 tree |
| `Ih Im Id Ir Is Ia Ii Il Ix` + `00`–`39` | item (base `tst2`) | Circle shop kinds × price steps (`Ix` = Experience) |
| `Iy Ik Ie` + `00`–`39`, `Ic00`, `Iw00` | item (base `tst2`) | Castle shop: health/armor/regen steps, repair, shockwave (1 tree each) |
| `Ip01`–`Ip08` | item | Premium items Lv 1 (sold) |
| `Iu<i><L>` (i 1–8, L 2–5) | item | Premium items Lv 2–5 (made by the merge, never sold) |
| `Xh Xm Xd Xa Xs Xg Xi Xl` + `00`–`39` | ability | Hero bonus abilities (bases `AIlf AImb AIat AId1 AIs1 AIa1 AIi1 AIx1`) |
| `Xk Xy Xr` + `00`–`39` | ability | Castle armor / max-HP / regen abilities (`AId1`, `AIlf`, `Arel`) |
| `Xp01`–`Xp08`, `Xu<i><L>` | ability | Premium item abilities Lv 1 / Lv 2–5 |
| `Xv08`–`Xv11`, `Xz09`–`Xz11` | ability (`AIlf`, `AIat`) | Gate level bonus HP / damage for its wave units and Protector |
| `Edry` | hero (base `Emoo`) | The Dryad — the only champion (Dryad model, spear missile) |
| `Xesp` `Xswt` `Xfsp` | hero ability (base `AEev`, 5 levels, 0 % evasion) | Dryad skills Extra Spear / Swift Throw / Fire Spears (level holders; effects in the script) |
| `Xsw1`–`Xsw5` | ability (base `AIsx`) | Hidden +20 % attack speed each, added on Swift Throw learn |
| `Xfor` | ability (base `AIfb`, 0 damage) | Hidden fire orb: fire missile once Fire Spears is learned |
| `dspr` `dspf` | unit (base `earc`, locust, scale 0.01) | Extra Spear dummies: one shot with the spear / fire missile, 4 s timed life |
| `Xatt` | hero ability (base `Aamk`) | Attributes: 100 levels, +10 all stats per level, learnable from hero level 11 |
| `Xcsh`, `Xcs2` | ability (bases `Aneu`, `Aall`) | Castle shop buyer selection, 3000 radius |
| `BTNCDStr/Agi/Int.blp` | imported icon | `ReplaceableTextures\CommandButtons\` (+ `CommandButtonsDisabled\DISBTN…`) |

## Coordinates

Arm-local `(u, v)`: u across, v outward; arm d = 0 N, 1 E, 2 S, 3 W (`from_arm`). Lane `L = 2d + side`.
Map 112×112 tiles (playable ±6400 x, -6656..6144 y). Plaza `|x|,|y| ≤ 1536`; lanes `|u| ∈ [384, 1024]`,
`v ∈ [1536, 4992)`; base rooms `v ∈ [4992, 5888]`;
tower `(±704, 3600)` (mid-lane), Nexus `(±704, 5440)`; hall at `(-3200, 3200)`; grove SE (`GROVE_RECTS`);
Dark Gate NE (`SHARED_RECTS`: corner room 1280–1920, leg to x 3840, leg up to y 3840, base room x 2944–4096 / y 3840–4864);
Shadow Gate SW (`LEVEL4_RECTS`, point mirror of the Dark Gate); Inferno Gate far SW (`LEVEL5_RECTS`: leg west out of the
L4 base room x -5376..-4096, chamber x -6272..-5376 / y -4864..-3840; its waves walk out through the L4 corridor);
all gate geometry per lane in `GATE_GEOMETRY`. Frozen Gate NW (`LEVEL3_RECTS`: corner room x -2048..-1280, leg west to x -5120 under the Hall, leg north at x -5120..-4480, base room x -5248..-4352 / y 3968–4864).
Wave units carry `userdata = lane*16 + waypoint` (gate units: 128–191).
