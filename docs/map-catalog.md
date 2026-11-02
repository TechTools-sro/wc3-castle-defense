# TechTools Castle Defence — player guide

8-player co-op hero lane defense for WarCraft III: The Frozen Throne **1.27b**. Made by TechTools; the whole map is
generated from code. Players 1–8 are human (race fixed — your champion is your race); the 4 enemy factions are
fixed computer players.

## Goal

Pick a champion, hold **your own lane**, destroy your lane's tower and Nexus, kill the boss that rises from the
ruins, then fight through the four shared **gate levels** (2–5). When every boss is dead the **final boss** rises at the castle: **win** by killing him. **Lose** when the Castle of Lordaeron in the middle falls.

## How a round goes

1. **Champion select (45 s):** click a champion in the Hall of Champions — 12 champions, free, several players may
   pick the same one. No walking needed.
2. **Your lane:** your champion spawns and revives on your Champion's Circle at your lane entrance.
3. **Waves: every lane has its own.** Your next wave comes **as soon as your lane is clear**, so clearing fast means stronger monsters and more gold, and nobody waits for anybody. After your every 10th wave you get a **1-minute
   shopping break**. Each cleared wave pays you `50 + 50 × your wave` gold and **1 tree**.
4. **Stages:** the tower stands mid-lane, far in front of the Nexus — take them one at a time. While your tower
   stands, basic units come out of it. Tower down → its **Tower Warden**, a boss of its own, rises on the ruins,
   the next wave comes at once and stronger units come out of the Nexus. Nexus down → its boss rises and the
   strongest units come out of the ruins until the boss dies. ⚠️ Towers hit for ~25 000 and Nexuses for ~27 500 per shot (20 000 / 15 000 HP) — every next building and gate
   level hits harder. Lane bosses with their gear: 120 000 HP and ~2400 per hit at wave 1, far more at later waves (986 400 HP and ~9300 at wave 20). Tower Wardens with their gear: 52 500 HP at wave 1, 137 500 at wave 10. **Bosses run at top speed, no stun holds them, and they wear bound gear: more HP, attack speed, critical hits, armor and spell resistance.**
5. **Fewer monsters, each far stronger, growing with every wave:** melee 700 HP / 60 damage, ranged 420 HP / 120 damage at wave 1; at wave 10 about 5900 / 275 and 3500 / 555, at wave 20 about 23 900 / 1030 and 14 300 / 2065. They start in ranks, melee in front, ranged behind. ×1.5 HP and ×1.25 damage after your tower falls, ×2 and ×1.5 in the boss stage. **Spend your 1000 gold at your Circle before the first wave.** **Kill gold:** a minion pays its lane's wave number in gold, more at higher waves (wave 5 → 7 gold, wave 20 → 50), double on Level 2, triple on
   Level 3.
6. **Wave size:** front line (melee) = 5 + wave, back line (ranged) = half the wave (max 16 + 8 per lane). Every 10th wave adds
   wave champions (1 at wave 10, 2 at wave 20, ... at most 6).
7. **Level 2 — the Dark Gate (NE):** opens when the first player destroys a Nexus. A shared lane with a stronger
   tower and Nexus; its monsters pay extra gold per kill. It goes on from the wave of the player who opened it and then counts by itself. Clearing a gate's wave pays **everyone** its gold and 1 tree.
8. **Level 3 — the Frozen Gate (NW)**, **Level 4 — the Shadow Gate (SW)** and **Level 5 — the Inferno Gate (far
   SW)** follow, each opening when the previous gate's Nexus falls and each harder (tower, Nexus, monsters, boss),
   with more gold per kill (×2 … ×5). Every gate Nexus raises a boss. With every lane boss and all gate bosses dead, the final boss rises.
   Gates are shared, so they have more HP with more players (×1.35 for 2, ×2.05 for 4, ×3.45 for 8): help each other there. The count is the players at the start of the round.

9. **The final boss — Kharazul the World Ender:** rises at the castle 30 s after the last boss falls (no more waves, the
   castle is shielded). 5 000 000+ HP (more with more players) and 20 000+ damage per hit — **all growing with the game
   minute**, also during the fight. **Stuns don't hold him**, and he stuns you: Storm Bolt, War Stomp, Inferno, Bash, plus
   Shockwave. Kill him to win.

## Shops

- **Champion's Circle** (your own shop, instant, +5 % price per buy): Health +600, Mana +75, Damage +20,
  Armor +8, Strength +20, Agility +20, Intelligence +20, All stats +10 — bonuses show as green stats — and
  **Experience +1 level** (250 gold).
- **The Castle** (select it, also while your champion is dead; 1 tree each): Castle Health +1000, Castle Armor +3, Castle Regeneration +10 HP/s (its button shows what was bought so far),
  Repair +2000 HP, Shockwave (a quarter of their HP off every wave monster near the castle).
- **Secret grove** (narrow passage at the SE corner of the plaza; its shops sell to your champion anywhere on the
  map — just select the shop): Fountain of Power (fast HP + mana),
  **Premium Armory** (1000 gold: lifesteal, attack speed, critical strike, bash, evasion, boots, regeneration,
  mana regeneration — buy the same item again for the next rank, up to 5: 5 / 10 / 15 / 20 / 30 % lifesteal, +5 to +25 % attack speed, 4 to 20 % chance of 2x, 3 to 15 % bash with +5 to +25 damage and a 0.5 s stun, 3 to 15 % dodge, +10 to +50 speed, +2 to +10 HP/s, +10 to +50 % mana regeneration), **Bank** (1 tree = +100 gold income every minute, up to 2 minutes per wave of your lane: holding your wave back stops it; once your lane is finished any wave renews it; during the final boss it pays all the time), **Apothecary** (potions heal % of max and stack in one slot — even with a full inventory: Healing 50 % HP and Mana 50 % mana for 100 gold, Restoration full HP + mana for 250, Invulnerability 200; staff of teleportation).

## EPIC loot

Every Nexus boss drops an EPIC crown: +200 all stats from a lane boss, +400 / +600 / +800 / +1000 from the Level 2–5
bosses.

## Champions

- Every level-up refills HP and mana; clearing your first wave gives level 2.
- Hero level is practically unlimited. All five skills are learned by hero level 20; from level 21 every level-up adds +30 to all stats.
- Skills on **Q W E R T**, innate ability on **D**, the level 20 ability on **F**.
- **12 champions from X Hero Siege 3.28, with their real abilities:**
  - **Dryad** — **Multiple Arrows**: every attack also throws spears at other enemies, up to 4 / 6 / 8 / 10 hit, each with the damage of her weapon. Evasion, Critical Arrows, two auras, poison.
  - **Mountain King** — Storm Bolt, Thunder Clap, Bash, Avatar. From level 20 Bolt and Clap strike twice.
  - **Tauren Chieftain** — Shockwave, War Stomp, Pulverize; level 20: Reincarnation.
  - **Pit Lord** — Rain of Fire, War Stomp, cleave, Doom, Finger of Death.
  - **Archmage** — Blizzard, Water Elemental, Frost Bolt, Starfall.
  - **Lich** — Frost Nova, Breath of Frost, Frost Arrows, Frost Beast.
  - **Paladin** — Healing Wave, Fan of Light, Pure Light; level 20: Light Frenzy resets cooldowns.
  - **Blademaster** — Wind Walk, Critical Strike, Mirror Image, Bladestorm; level 20: splits into 3.
  - **Beastmaster** — bears, wolves, hawks, Stampede; level 20: Terror Wolf.
  - **Crypt Lord** — Impale, Spiked Carapace, Carrion Beetles, Locust Swarm.
  - **Demon Hunter** — Immolation, Negative Energy, Metamorphosis.
  - **Priestess of the Moon** — Chain Lightning, Forked Lightning, Monsoon.

## Commands

| Command | Does |
|---|---|
| `-help` | shows the commands |
| `-zoom 250` | zoom out (`-zoom` = normal) |
| `-cam` / Esc | camera follows your hero |
| Space | jump to your hero |
| `-break 60` | shopping break length in seconds (5–300) |
| `-wave 5` | seconds between waves (0–60, default 0) |

## Scoreboard

Top right: game time, castle HP (current / max) and per player level, **his wave**, kills, deaths and income (gold per minute). An opened gate adds a row with its wave.
