# Gameplay spec

The binding description of how the map plays. Numbers name their source so they can be changed in one place.
Update this file in the same change as the behaviour.

## Players and lobby

| Slot | Who | Notes |
|---|---|---|
| Player 1–8 (ids 0–7) | Humans, team 1 | Race fixed Human (your champion is your race). Lane `L` = Player `L` |
| Player 9–12 (ids 8–11) | Invader computers, team 2 | Fixed (flag 0x20), Undead in the lobby, not removable |
| Player 15 (id 14) | "Kingdom of Lordaeron" | Owns the castle; allied (passive + shared vision) with players |

Invader of arm `d` = Player(8 + d): 0 North **The Scourge**, 1 East **The Burning Legion**, 2 South
**The Tidal Horde**, 3 West **The Wildland Clans** (`FACTIONS` in `gen/objects.py`).

## Round flow

1. **Champion select** (45 s, `SELECT_TIME`). Camera on the Hall of Champions; 5 taverns in a tight ring
   (Alliance, Horde, Scourge, Sentinels, Mercenaries; 24 heroes, `TAVERNS`). Click a hall, click a hero — free,
   each hero once. An invisible helper unit does the buying (no walking). A big gold **"Select a Champion"**
   floats over the hall for players who haven't picked. Time out → random hero.
2. **Start.** Hero appears on the player's **Champion's Circle** (lane entrance), lane hint (coloured circle,
   floating "Name's lane", minimap ping). One message: "Defend your lane! -help = commands".
   Starting gold **1000** (`SetupChampionSelect`).
3. **Waves.** First wave 30 s after the pick (`FIRST_WAVE_DELAY`). The next countdown starts only when **every
   wave monster on every lane is dead**: then **10 s** (`WAVE_INTERVAL`), or a **2 min break after every 5th
   wave** (`WAVE_BREAK`). The timer is hidden while monsters are alive.
   The break is a **shopping break**: "BREAK - Time to go Shopping!", gold minimap pings + effects on the grove
   entrance and every grove building (`ShoppingTime`). Bosses don't hold the waves.
4. **Push.** Each lane has its own tower (in front) and Nexus (behind). Tower destroyed → waves come out of the
   Nexus, stronger. **Nexus destroyed → that lane's boss rises** (+150 gold to all). Boss slain → +250 gold to all.
5. **The Dark Gate** opens when the first player destroys his Nexus (see below).
6. **Win** when every active lane's boss is dead **and the Dark Citadel is destroyed**. **Lose** when the castle dies. End dialog: *Play again*
   (full reset → champion select, fresh castle, prices reset, taverns restocked) or *Finish game*.

Only active lanes (player present) have monsters, a base and an open gate; empty lanes stay gated.

## Waves (`SpawnWave`, `LaneStage` in `gen/castle_logic.j`)

Standardized: the **lane stage picks the unit types**, the wave number only adds units.

| Stage | When | Spawns from | Units (front / back) |
|---|---|---|---|
| 0 | tower standing | the tower | stage-0 pair of the faction |
| 1 | tower destroyed | the Nexus | stage-1 pair (stronger) |
| 2 | Nexus destroyed, boss alive | the ruins | stage-2 pair (strongest) |
| — | boss slain | — | the lane stops |

- **Front line** (melee) = `4 + wave` (wave 1 → 5, +1 per wave, max 30). **Back line** (ranged) = `wave / 2`
  (+1 every 2 waves, max 15). Every 10th wave adds **wave/10 weakened champions** per lane (800 HP, armor 2, 30+1d8, normal size; `nc{d}0`,
  `WAVE_CHAMP_*`), announced one wave before. Constants `WAVE_*` in `gen/objects.py`.
- Rosters: `FACTIONS[d]["stages"]` / `SHARED["stages"]` in `gen/objects.py` (3 × (front, back) unit ids per faction).
- Dark Gate units: its own stages (stronger pairs), +300 HP each (`AIl2`), red tint.
- Gold per wave to every player: `50 + 50*wave` → 100, 150, 200, … (no cap), paid when the wave is **cleared** (with the tree).
- **Tower destroyed** (`OnTowerDestroyed`, also the Dark Spire): a **Protector** (the faction champion, 1.5× size,
  +450 HP, gold tint) appears between the ruins and the Nexus and stays leashed there (`ProtectorTick`), and that
  lane's next wave spawns **at once** (already stage 1).
- Monsters attack-move along the lane waypoints (`WaveUnitTick`, 1 s) to the castle.

## The Dark Gate (shared lane, NE — lane 8 / arm 4 in the script)

- Closed by a gate (`SHARED_GATE`) until the **first** player destroys his Nexus (`OpenSharedPath`).
  Then the gate opens, the **Dark Spire** (4000 HP, armor 8, 140 + 2d15 chaos, range 800; in the north leg) and the
  **Dark Citadel** (80 000 HP, armor 15, 650 + 4d25 chaos missile every 2.5 s, range 700) appear, and every wave
  also spawns there.
- Its waves follow the same stage rule with the Dark Gate roster (stage 0 while the Spire stands, 1 after).
- Every Dark Gate kill pays the killer **+(15 + wave) gold** extra (floating gold number, `SharedBounty`).
- Dark Citadel destroyed: +500 gold to all; required for victory. A restart closes the gate again.
- Geometry `SHARED_RECTS` in `gen/layout.py`: corner room at the plaza's NE corner → east-west leg →
  north leg → base room in the top-right corner. Owner: the Scourge computer (Player 9).

## Trees and the Bank

- Every cleared wave (all monsters dead) gives every player **+1 tree** (lumber, top bar).
- The **Bank** (secret grove, gold-mine look) sells **Income +100** for **1 tree**: +100 gold every minute,
  stacks without limit (`BANK_ITEM`, `INCOME_STEP`, `IncomeTick` every 60 s). Restart resets income and trees.

## Champions

- Spells on **Q W E R** for cast and learn, tooltips retagged `[Q]` (`gen/hotkeys.py`).
- Every hero can attack **air** units, melee heroes too (`ua1g` += air, `original_unit_mods`).
- **Hero level is practically unlimited** (`MAX_HERO_LEVEL` = 1000 via `war3mapMisc.txt`). Spells are maxed at
  level 10; from level 11 each skill point goes into **Attributes** (`Xatt`, learn key T): +3 Str/Agi/Int per
  level, 100 levels (hero level 110). Above that every level-up adds +3 to all three automatically.
- **Level 2** when the player's first wave is cleared (or at wave 2 for everyone). Every level-up refills HP + mana.
- Death → revive on the Champion's Circle after `4 + 2*level` s, max 24 s (`StartRevive`). Deaths counted.

## Champion's Circle shop (per player, `KINDS_DEF` rows 1–2 in `gen/objects.py`)

| Slot | Key | Item | Gives | Base price |
|---|---|---|---|---|
| 1,1 | Q | Health | +100 max HP | 100 |
| 2,1 | W | Mana | +75 max mana | 100 |
| 3,1 | E | Damage | +5 damage | 100 |
| 4,1 | R | Armor | +2 armor | 100 |
| 1,2 | A | Strength | +10 Str | 100 |
| 2,2 | S | Agility | +10 Agi | 100 |
| 3,2 | D | Intelligence | +10 Int | 100 |
| 4,2 | F | All stats | +3 Str/Agi/Int | 100 |

- Instant: each buy adds a hidden item-bonus ability copy → shows as a **green +N**, base stats untouched.
- Every buy +10 % for that player and kind (`STAT_PRICE_GROWTH`), 40 steps (`STAT_TIERS`).
- Tooltip: `Agility  Lv 3  (S)` (Lv = times bought, light blue) / `+10 Agility` / orange `Next buy: +10% gold`.
- Icons: game's own hero-attribute icons for Str/Agi/Int (`gen/icons.py`), Heal / Brilliance / Attack /
  Defend / StatUp for the rest.

## Castle (`hcd0`): 8000 HP, armor 10 — and the castle shop

Select the castle and buy with a champion anywhere on the plaza (3000 radius). Every castle buy costs
**1 tree** (`CASTLE_TREE_COST`), no gold. Everyone sees "Name: +3 castle armor".

| Key | Buy | Effect |
|---|---|---|
| Q | Castle Health | +1000 max HP (stacks) |
| W | Castle Armor | +3 armor (stacks) |
| E | Castle Regeneration | +10 HP per second (stacks) |
| R | Repair Castle | +2000 HP heal (repeatable) |
| A | Shockwave | 300 + 30 × wave magic damage to every monster within 1100 of the castle (repeatable) |

Stacking upgrades use one hidden ability per buy (global counter, 40 max). Works while the buyer's champion is
dead. A restart replaces the castle, so upgrades reset. The castle deals no damage on its own.
⚠️ The castle is owned by the neutral-extra player (15); its shop carries both a neutral-building (`Xcsh`, `Aneu`)
and an allied shop-sharing (`Xcs2`, `Aall`) buyer ability — the `Aall`-only version could not be used in-game.

## Secret grove (narrow passage at the SE plaza corner)

- **Fountain of Power**: 2 % max HP + 2 % max mana per second.
- **Bank**: trees → passive income (see above).
- **Premium Armory** — 8 simple items, **1000 gold** each, stock 3, restock 30 s (`PREMIUM_DEF`), hotkeys
  Q W E R / A S D F. **Upgradable to Lv 5:** buying an item you already hold merges both into the next level
  (`TryUpgradePremium`); at Lv 5 a new buy is refunded. Lv 1 → Lv 5:

  | Item | Lv 1 | per level | Lv 5 |
  |---|---|---|---|
  | Vampire Fang | 30 % lifesteal | +10 % | 70 % |
  | Fury Gloves | +40 % attack speed | +15 % | +100 % |
  | Executioner's Axe | 20 % chance for 3× damage | +5 % | 40 % |
  | Stormhammer | 20 % stun 1 s, +40 dmg | +5 %, +20 dmg | 40 %, +120 |
  | Phantom Cloak | 25 % dodge | +5 % | 45 % |
  | Winged Boots | +100 move speed | +25 | +200 (engine cap 522) |
  | Troll Heart | +15 HP/s | +10 | +55 |
  | Arcane Mask | +150 % mana regen | +50 % | +350 % |
- **Apothecary**: potions, scrolls, boots, rings, staff of teleportation (`SHOPS["apothecary"]`), stock 8, restock 10 s.

## Enemy bases and bosses (`gen/objects.py`)

- Tower: 1800 HP, armor 4, 85 + 2d10 chaos / 1.3 s, range 750 — in the lane, far in front of the Nexus
  (`tower_pos`, v = 2900) so their ranges never overlap: tower first, then its stronger waves, then the Nexus.
- **Nexus: 30 000 HP, armor 10, huge attack** 450 + 4d20 chaos missile every 2.5 s, range 700, hits air too
  (`BASE_HP`, `NEXUS_*`, `nexus_attack`).
- Boss strength by player count: 1–2 / 3–5 / 6–8 players → 3500 / 6000 / 9000 HP, armor 3 / 4 / 5.
  Bosses cast spells, summon, and are leashed to their ruins (`BossTick`).

## UI and commands

- **Scoreboard** (top right, 1 s refresh): title `m:ss    Wave N    Castle HP / max HP` (game time from the end of champion select, stops at the end;
  max HP includes Castle Health upgrades). The end dialog shows the time ("VICTORY in 23:45!").; columns Player · Lv · Kills · Deaths.
- **-help** (only to the asker): gold `Commands`, then light-blue command + grey description per line:
  `-zoom 250` zoom out · `-cam` camera follows your hero · `Space` jump to your hero · `-break 60` · `-wave 5`.
- **Pace settings** (any player, announced to all; `OnConfigChat`): `-break N` = shopping-break length (5–300 s,
  default 120), `-wave N` = seconds between waves (1–60 s, default 10). No number = show the current values.
  A countdown already running is shortened at once if it is longer than the new value; kept across *Play again*.
- **-zoom N**: 250 = distance 2500 (also accepts the raw distance); `-zoom` alone = normal. Remembered.
- **Esc / -cam**: camera follows the champion. **Space**: jumps to the champion (quick position kept on him).
- F9 quests: "Defend your lane" + short tips.
- **Hidden developer cheats** (not in -help, only for player names in `DEV_NAMES` in `build.py`):
  `-addmoney 500`, `-addwood 10` / `-addtree 10`, `-lvl 5` (no number = 1000 gold / 10 trees / 1 level).
- Dark map: permanent midnight, no fog of war, Icecrown walls and gates, torches.

## Art

- Lobby/preview icon (`render_icon`): TechTools mark + TECHTOOLS, stone castle with blue windows,
  undead attackers with red glow from both sides, CASTLE / DEFENCE in WarCraft gold.
- Loading screen (`render`): flat dark navy, mark + TECHTOOLS + gold CASTLE DEFENCE + tagline on the far
  right (the game draws the player list over the left ~62 %). Low-res tiles on purpose.
