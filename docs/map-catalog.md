# TechTools Castle Defence — player guide

8-player co-op hero lane defense for WarCraft III: The Frozen Throne **1.27b**. Made by TechTools; the whole map is
generated from code. Players 1–8 are human (race fixed — your champion is your race); the 4 enemy factions are
fixed computer players.

## Goal

Pick a champion, hold **your own lane**, destroy your lane's tower and Nexus, kill the boss that rises from the
ruins, and destroy the **Dark Citadel** behind the Dark Gate. **Win** when every boss is dead and the Dark Citadel
has fallen. **Lose** when the Castle of Lordaeron in the middle falls.

## How a round goes

1. **Champion select (45 s):** click a hall, click a hero (24 heroes, free, each one once). No walking needed.
2. **Your lane:** your champion spawns and revives on your Champion's Circle at your lane entrance.
3. **Waves:** the next wave comes 10 s after every monster is dead; after every 5th wave there is a **2-minute
   shopping break**. Each cleared wave pays every player `50 + 50 × wave` gold and **1 tree**.
4. **Stages:** while your tower stands, basic units come out of it. Tower down → a **Protector** guards the Nexus,
   the next wave comes at once and stronger units come out of the Nexus. Nexus down → its boss rises and the
   strongest units come out of the ruins until the boss dies.
5. **Wave size:** front line (melee) = 4 + wave, back line (ranged) = +1 every 2 waves. Every 10th wave adds
   weakened champions (1 at wave 10, 2 at wave 20, ...).
6. **The Dark Gate (NE):** opens when the first player destroys a Nexus. A shared lane with a stronger tower and
   Nexus; its monsters pay extra gold per kill.

## Shops

- **Champion's Circle** (your own shop, instant, +10 % price per buy): Health +100, Mana +75, Damage +5,
  Armor +2, Strength +10, Agility +10, Intelligence +10, All stats +3 — bonuses show as green stats.
- **The Castle** (select it; 1 tree each): Castle Health +1000, Castle Armor +3, Castle Regeneration +10 HP/s,
  Repair +2000 HP, Shockwave (damages every monster near the castle).
- **Secret grove** (narrow passage at the SE corner of the plaza): Fountain of Power (fast HP + mana),
  **Premium Armory** (1000 gold: lifesteal, attack speed, critical strike, bash, evasion, boots, regeneration,
  mana regeneration), **Bank** (1 tree = +100 gold income every minute), Apothecary (potions, scrolls).

## Champions

- Spells on **Q W E R**; every level-up refills HP and mana; clearing your first wave gives level 2.
- Hero level is practically unlimited. After level 10 (spells maxed) skill points go into **Attributes**
  (learn key T): +3 Strength, Agility and Intelligence per level.
- All heroes, melee too, can attack flying units.

## Commands

| Command | Does |
|---|---|
| `-help` | shows the commands |
| `-zoom 250` | zoom out (`-zoom` = normal) |
| `-cam` / Esc | camera follows your hero |
| Space | jump to your hero |

## Scoreboard

Top right: wave, castle HP (current / max) and per player level, kills and deaths.
