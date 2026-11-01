# TechTools Castle Defence — player guide

8-player co-op hero lane defense for WarCraft III: The Frozen Throne **1.27b**. Made by TechTools; the whole map is
generated from code. Players 1–8 are human (race fixed — your champion is your race); the 4 enemy factions are
fixed computer players.

## Goal

Pick a champion, hold **your own lane**, destroy your lane's tower and Nexus, kill the boss that rises from the
ruins, then fight through the four shared **gate levels** (2–5). **Win** when every boss is dead. **Lose** when the Castle of Lordaeron in the middle falls.

## How a round goes

1. **Champion select (45 s):** click the **Dryad** in the Hall of Champions — everyone plays her, free. No walking
   needed.
2. **Your lane:** your champion spawns and revives on your Champion's Circle at your lane entrance.
3. **Waves:** the next wave comes 10 s after every monster is dead; after every 5th wave there is a **2-minute
   shopping break**. Each cleared wave pays every player `50 + 50 × wave` gold and **1 tree**.
4. **Stages:** the tower stands mid-lane, far in front of the Nexus — take them one at a time. While your tower
   stands, basic units come out of it. Tower down → a **Protector** guards the Nexus,
   the next wave comes at once and stronger units come out of the Nexus. Nexus down → its boss rises and the
   strongest units come out of the ruins until the boss dies. ⚠️ The Nexus has only 3 000 HP but a huge attack (~1000 per shot).
5. **Monsters:** melee 200 HP / 30 damage, ranged 120 HP / 60 damage; ×2 after your tower falls, ×3 in the boss
   stage. **Kill gold:** a minion pays as much gold as the wave number (wave 5 → 5 gold), double on Level 2, triple on
   Level 3.
6. **Wave size:** front line (melee) = 4 + wave, back line (ranged) = +1 every 2 waves. Every 10th wave adds
   weakened champions (1 at wave 10, 2 at wave 20, ...).
7. **Level 2 — the Dark Gate (NE):** opens when the first player destroys a Nexus. A shared lane with a stronger
   tower and Nexus; its monsters pay extra gold per kill.
8. **Level 3 — the Frozen Gate (NW)**, **Level 4 — the Shadow Gate (SW)** and **Level 5 — the Inferno Gate (far
   SW)** follow, each opening when the previous gate's Nexus falls and each harder (tower, Nexus, monsters, boss),
   with more gold per kill (×2 … ×5). Every gate Nexus raises a boss. Win = every lane boss and all gate bosses dead.

## Shops

- **Champion's Circle** (your own shop, instant, +3 % price per buy): Health +100, Mana +75, Damage +5,
  Armor +2, Strength +20, Agility +20, Intelligence +20, All stats +10 — bonuses show as green stats — and
  **Experience +1 level** (250 gold).
- **The Castle** (select it; 1 tree each): Castle Health +1000, Castle Armor +3, Castle Regeneration +10 HP/s,
  Repair +2000 HP, Shockwave (damages every monster near the castle).
- **Secret grove** (narrow passage at the SE corner of the plaza; its shops sell to your champion anywhere on the
  map — just select the shop): Fountain of Power (fast HP + mana),
  **Premium Armory** (1000 gold: lifesteal, attack speed, critical strike, bash, evasion, boots, regeneration,
  mana regeneration — buy the same item again to upgrade it, up to Lv 5), **Bank** (1 tree = +10 gold income every minute), **Apothecary** (potions heal % of max and stack in one slot: Healing 50 % HP and Mana 50 % mana for 100 gold, Restoration full HP + mana for 250, Invulnerability 200; staff of teleportation).

## EPIC loot

Every Nexus boss drops an EPIC crown: +200 all stats from a lane boss, +400 / +600 / +800 / +1000 from the Level 2–5
bosses.

## Champions

- Spells on **Q W E R**; every level-up refills HP and mana; clearing your first wave gives level 2.
- Hero level is practically unlimited. After level 10 (spells maxed) skill points go into **Attributes**
  (learn key T): +10 Strength, Agility and Intelligence per level.
- All heroes, melee too, can attack flying units.
- The **Dryad** throws spears. **Q Extra Spear**: +1 spear per level at another enemy, full damage. **W Swift
  Throw**: +20 % attack speed per level. **E Fire Spears**: +20 % fire damage on every hit per level. 5 levels each.

## Commands

| Command | Does |
|---|---|
| `-help` | shows the commands |
| `-zoom 250` | zoom out (`-zoom` = normal) |
| `-cam` / Esc | camera follows your hero |
| Space | jump to your hero |
| `-break 60` | shopping break length in seconds (5–300) |
| `-wave 5` | seconds between waves (1–60) |

## Scoreboard

Top right: game time, wave, castle HP (current / max) and per player level, kills, deaths and income (gold per minute).
