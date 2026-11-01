# Gameplay spec

The binding description of how the map plays. Numbers name their source so they can be changed in one place.
Update this file in the same change as the behaviour.

## The map (v4.3, Jiří: too narrow at high waves)

128 × 128 tiles (was 112). Every lane and gate corridor is **1280 wide** (was 640), the plaza 4608 wide (was 3072). A lane is as long as before: Circle to tower 1776, Circle to spawn 1536. **Only the plaza grew: a leak walks about 720 further to the castle** (lane 4370, was 3653; Levels 2–4 6128, was about 5200; Level 5 9616, was 7765), and a champion crossing the plaza takes about 3 s longer. Every entrance has a gate of two pieces. `tools/layout_audit.py` checks all of it and draws it.

## Players and lobby

| Slot | Who | Notes |
|---|---|---|
| Player 1–8 (ids 0–7) | Humans, team 1 | Race fixed Human (your champion is your race). Lane `L` = Player `L` |
| Player 9–12 (ids 8–11) | Invader computers, team 2 | Fixed (flag 0x20), Undead in the lobby, not removable |
| Player 15 (id 14) | "Kingdom of Lordaeron" | Owns the castle; allied (passive + shared vision) with players |

Invader of arm `d` = Player(8 + d): 0 North **The Scourge**, 1 East **The Burning Legion**, 2 South
**The Tidal Horde**, 3 West **The Wildland Clans** (`FACTIONS` in `gen/objects.py`).

## Round flow

1. **Champion select** (45 s, `SELECT_TIME`). Camera on the Hall of Champions — a small walled room (768 × 768, `HALL_CENTRE` / `HALL_HALF`), far from every spawn: **one** tavern (sells within 600 only) with **12 champions** on its 12 buttons (`TAVERN_KEYS` Q W E R / A S D F / Z X C V; stock 8 each, so several players may pick the same one). An invisible helper unit does the buying (no walking). **One champion per player per round** is the map's own rule (`OnUnitSold`): only a playing player without a champion, during the selection, from this tavern, for one of the 12; anything else sold is removed at once. The game's own hero limits are off, see the gotchas. A big gold **"Select a Champion"** floats over the hall for players who haven't picked. Time out → a random champion (untaken first). See **Champions** below.
2. **Start.** Hero appears on the player's **Champion's Circle** (lane entrance), lane hint (coloured circle,
   floating "Name's lane", minimap ping). One message: "Defend your lane! -help = commands".
   Starting gold **1000** (`SetupChampionSelect`). A second message tells players to spend it at the Circle: the first wave is strong.
3. **Waves.** **Every lane has its own wave** (see below). First wave 30 s after the pick (`FIRST_WAVE_DELAY`), on every lane. A lane's
   next countdown starts only when **that lane's wave monsters are dead**: then **at once** (`WAVE_INTERVAL` = 0 s since v3.5), or a **1 min
   break after its every 10th wave** (`WAVE_BREAK`, `BREAK_EVERY`). The timer is hidden while its monsters are alive, and only the lane's player sees it.
   The break is that player's **shopping break**: "BREAK - Time to go Shopping!", gold minimap pings only he sees + effects on the grove
   entrance and every grove building (`ShoppingTime`). Bosses don't hold the waves.
4. **Push.** Each lane has its own tower (in front) and Nexus (behind). Tower destroyed → waves come out of the
   Nexus, stronger. **Nexus destroyed → that lane's boss rises** (+150 gold to all). Boss slain → +250 gold to all.
5. **Levels.** Level 1 = the player lanes; Levels 2–5 are shared gate lanes, each harder, opening one after the
   other (see below).
6. **Final boss** when every active lane's boss is dead **and all four gate levels are cleared** (see below). **Win** when he dies. **Lose** when the castle dies (shielded during his fight). End dialog: *Play again*
   (full reset → champion select, fresh castle, prices reset, taverns restocked) or *Finish game*.

Only active lanes (player present) have monsters, a base and an open gate; empty lanes stay gated.

## Waves (`SpawnWave`, `LaneStage` in `gen/castle_logic.j`)

Standardized: the **lane stage picks the unit types**, the lane's own wave number adds units and strength.

### Every lane has its own wave (v4.2, `gLaneWave`, `StartLaneWave`, `OnLaneCleared`)

Jiří: every lane has its own wave level, each player his own, based on how fast he clears it. A fast player climbs, a slow one holds back nobody but himself. No catch-up.

| | A player's lane (0–7) | A shared gate (8–11) |
|---|---|---|
| Wave starts | 0; its first wave 30 s after the pick | The wave of the lane that opened it (Level 2: the player whose Nexus fell first, Level 3: Level 2, ...); its next wave is one higher and comes 30 s after it opens |
| Next wave | When **that lane's** monsters are dead | Same |
| Break | After that lane's every 10th wave: its player's shopping break | After the gate's every 10th wave: only the gate pauses |
| Clear pays | `50 + 50 × its wave` gold + 1 tree **to that lane's player** | The same formula with the gate's wave **to every player** |
| News | To that lane's player only | To everyone, one line per clear; no line when a gate's wave starts |
| Ends | With its boss: no new wave. Monsters still alive pay when they are dead | Same |

- Every number that followed "the wave" follows the lane's wave now: size, HP, damage, kill gold, wave champions, Tower Wardens, bosses.
- **A player who left:** his lane goes on at its own wave, and its clears pay every other player, because they are the ones clearing it. Its news goes to everyone.
- **A finished lane's player** still earns on the gates (kills, clears) and from the Bank.
- **Consequence:** a lane does not rest while another is being cleared, so helping a friend costs time on your own lane, whose monsters keep marching. There is no team pause any more.

| Stage | When | Spawns from | Units (front / back) |
|---|---|---|---|
| 0 | tower standing | the tower | stage-0 pair of the faction |
| 1 | tower destroyed | the Nexus | stage-1 pair (stronger) |
| 2 | Nexus destroyed, boss alive | the ruins | stage-2 pair (strongest) |
| — | boss slain | — | the lane stops |

- **v4.3 (Jiří: far too many weak monsters): fewer, far stronger.** **Front line** (melee) = `5 + wave` (wave 1 → 6, max 16). **Back line** (ranged) = `(wave + 1) / 2`
  (max 8) — `WAVE_FRONT_*`, `WAVE_BACK_*`. Every 10th wave adds **wave/10 wave champions**, at most 6, per lane (base 2100 HP, armor 3, 90 damage, normal size, growing like the rest; `nc{d}0`,
  `WAVE_CHAMP_*`), announced one wave before. Constants `WAVE_*` in `gen/objects.py`.
- **Monsters scale by the wave (v4.1, Jiří: stronger monsters, predictable scaling), with `n = wave − 1`:** HP × (1 + 0.092 n²), damage × (1 + 0.045 n²). HP grows faster than damage.
  `WAVE_*` in `gen/objects.py`, `ScaleHpBonus` / `ScaleDmgBonus` in the script. The added bonus is rounded down to steps of 100 HP and 5 damage.

  | | Wave 1 HP / damage | Wave 5 | Wave 10 | Wave 20 | Wave 30 |
  |---|---|---|---|---|---|
  | Melee | 700 / 60 | 1700 / 100 | 5900 / 275 | 23 900 / 1030 | 54 800 / 2330 |
  | Ranged | 420 / 120 | 1020 / 205 | 3520 / 555 | 14 320 / 2065 | 32 820 / 4660 |
  | Wave champion | 2100 / 90 | 5100 / 150 | 17 700 / 415 | 71 800 / 1550 | 164 500 / 3495 |

  Melee: every 1.5 s, range 100, armor 2. Ranged: every 1.8 s, range 500, armor 0. Wave champion: every 1.5 s, armor 3.
- **Tower down ×1.5 HP, ×1.25 damage. Nexus down ×2 HP, ×1.5 damage** (`WAVE_STAGE_HP`, `WAVE_STAGE_DMG`), for melee and ranged; a wave champion has no stage factor.
- **Every faction fights alike:** attack type normal, no spells, no regeneration, same speed and armor. The model and its movement type stay its own: a few fly or hover (frost wyrms, banshees, revenants) or swim (nagas), and those can cross terrain a walker cannot.
- **A rescale never heals:** a unit keeps its actual HP when its maximum changes, cut only if the new maximum is lower (`ScaleKeepHp`). Applying a scale twice changes nothing. A bonus past the last bit stays at the maximum, it never wraps (`ScaleClamp`; +3 276 700 HP, +81 915 damage). `check_scaling` fails the build if a monster gets weaker with the wave or if a bonus would saturate before wave 80; at the current values none does.
- **A whole wave pays the gold and XP it paid with up to 60 monsters** (`WavePayRatio`): a regular monster's kill gold = its lane's wave × (the old count / the new count), up to ×2.5, and the rest of the XP on top of the game's own (`UnitKillXp`). A wave champion pays its wave, as before. × the level on the gate lanes (×2 … ×5), to
  the killer (`MinionBounty`; wave unit types have built-in bounty 0 via `NO_BOUNTY`). Towers, Nexus, bosses and
  Tower Wardens keep their normal bounty.
- Gold per wave: `50 + 50*wave` → 100, 150, 200, … (no cap), paid when the lane's wave is **cleared** (with the tree), see the table above for who gets it.
- **Tower destroyed** (`OnTowerDestroyed`, also the Dark Spire): **where the tower lay a boss rises, its Tower Warden** (v4.4, Jiří), see Enemy bases and bosses, and that
  lane's next wave spawns **at once** (already stage 1).
- Monsters attack-move along the lane waypoints (`WaveUnitTick`, 1 s) to the castle.

## Levels 2–5 — the gate lanes (shared by everyone, `GATE_LEVELS` in `gen/objects.py`)

Each level opens when the previous level's Nexus falls (Level 2: the first player Nexus), with its own wave and a scoreboard row (`OpenGateLane`, `BoardAddGate`). A gate Nexus that falls
raises the level's **boss** from its ruins; waves keep coming from the ruins until the boss dies (= level cleared).
Higher level = harder.

| | L2 Dark Gate | L3 Frozen Gate | L4 Shadow Gate | L5 Inferno Gate |
|---|---|---|---|---|
| Where | NE | NW | SW (mirror of L2) | far SW, a chamber behind the L4 base |
| Tower HP / dmg | 32 500 / ~35 000 | 50 000 / ~45 000 | 75 000 / ~60 000 | 105 000 / ~80 000 |
| Nexus HP / dmg | 40 000 / ~38 500 | 75 000 / ~49 500 | 125 000 / ~66 000 | 200 000 / ~88 000 |
| Wave monsters | HP ×1.25, damage ×1.1 | ×1.5, ×1.2 | ×1.75, ×1.3 | ×2, ×1.4 |
| Boss (×lane boss HP; HP / dmg) | Malgrath the Dark Lich ×3; 180 000 / ~3350 | Kel'Thar the Frozen Tide ×5; 300 000 / ~4300 | Azgaroth the Shadow Lord ×8; 480 000 / ~6200 | Infernus the World Breaker ×12; 720 000 / ~8100 |
| Kill gold per minion | 2 × wave | 3 × wave | 4 × wave | 5 × wave |
| Nexus down / boss slain | +500 / +500 | +1000 / +1000 | +2000 / +2000 | +3000 / +3000 |

- Lanes 8–11 / arms 4–7 in the script (`OpenGateLane`, `OnGateNexusDestroyed`, `OnGateBossSlain`, `gGateState`:
  -1 closed, 0 open, 1 boss alive, 2 cleared), all owned by the Scourge computer (Player 9). Geometry per lane in
  `GATE_GEOMETRY` (`gen/layout.py`). Tower in the leg far in front of the Nexus (no range overlap).
- Tower down → its **Tower Warden** on the ruins (level colour) + instant wave.
- **A wave starts in ranks (v4.3):** ranged at the back, melee in front of them, wave champions first, across the lane and looking at its first waypoint (`WaveAnchor`, `SpawnRanks`, `FORM_*`: 8 a rank, 128 apart; 96 made the engine swap ranks with big units). This is the order at the spawn, not a formation in battle: once they march and fight, the game moves them as it likes, and fliers pass ahead.
- **The team scales shared obstacles, mainly in HP:** gate wave monsters, Tower Wardens, towers, Nexuses and bosses × `1 + 0.35 × (team − 1)` (1 / 2 / 4 / 8 players: ×1, ×1.35, ×2.05, ×3.45; `TEAM_HP_PER_PLAYER`). Their damage does not depend on the team. Personal lanes never do: each player already adds a lane.
- **The team** (`gTeamCount`) is the number of players at the start of the round. Leaving during the round lowers nothing, because the others can control that champion (`OnPlayerLeave`) and his lane goes on at its own wave. A player who picked and left before the round began has no lane, no champion and does not count. A real leave has not been tested in a game: the hidden test has one player.
- Bosses copy their spells/summons from a lane boss (L2 Lich, L3 Tidelord, L4/L5 Pit Lord), armor +2 per level.
- A restart closes all gates again. **Victory needs all four levels cleared** plus every lane boss.

## Trees and the Bank

- Every cleared wave of your lane (all its monsters dead) gives you **+1 tree** (lumber, top bar); a cleared gate wave gives everyone +1.
- The **Bank** (secret grove, gold-mine look) sells **Income +100** for **1 tree**: +100 gold every minute,
  stacks without limit (`BANK_ITEM`, `INCOME_STEP`). Restart resets income and trees.
- **Bank clock (v4.1, per player since v4.2):** one payment per 60 counted seconds (`BankTick`). Every wave of your lane gives your clock 120 s to count (`INCOME_WAVE_SECONDS`), and only your next wave renews that: holding a wave with a last monster, a kill now and then or a long break pays 2 minutes at most, then "Bank stopped until your next wave". Once your lane is finished any wave anywhere renews it, because you have nothing left to hold (`BankRenew`). The final fight always counts.

## The final boss (v4.0, `FINAL_*` in `gen/objects.py`, `StartFinalBoss` … in `gen/castle_logic.j`)

**Kharazul the World Ender** (`nbf0`, Archimonde's model at scale 2.4, ranged 700, 320 speed).

- **When:** every active lane boss and all 4 gate levels are done (`CheckVictory` → `StartFinalBoss`). Waves stop for
  good, the castle is shielded (invulnerable), a 30 s warning runs (`FINAL_DELAY`), then he rises south of the castle
  (`FINAL_BOSS_POS`). **His death wins the game** (`OnFinalBossDead`). He is leashed to the plaza and the lane entrances
  (`FINAL_LEASH` 2500 from the castle), so revived champions are back quickly.
- **Stats follow the game clock**, minute m, at spawn and on every new minute of the fight (`FinalApplyStats`). **Growing never heals him (v4.1):** his actual HP stays, only his maximum rises. (Keeping the percentage, as before, gave him free HP every minute.)
  - max HP = (5 000 000 + 250 000 × m) × 1 / 2 / 3 for a team of 1–2 / 3–5 / 6–8, rounded down to 100 000; regen 500 HP/s
  - damage = 20 000 + 1000 × m chaos, every 1.2 s; armor = 30 + m / 2
  - spell tier +1 every 5 minutes (10 tiers); he goes up via "bit" abilities (`FinalBits`, steps 100 000 HP / 100 damage / 1 armor)
- **Stuns don't hold him:** `FinalImmuneTick` (0.05 s) removes the stun buffs at once and shows "Stun immune!".
- **His own skills** (`FinalBossTick`, damage × tier 1–10): Storm Bolt every 6 s (4000, 2.5 s stun), War Stomp every 8 s
  (3000, 450 area, 2 s stun), Shockwave every 11 s (4000, 1200 long), Inferno every 20 s (5000, 300 area, 2 s stun + an
  Infernal for 30 s), passive Bash (25 %, 1 s). Targets: nearest champion within 900 first, never an invulnerable unit.
- The scoreboard title shows his HP during the fight.

## EPIC boss loot (`EPIC_ITEMS`, `DropEpic`)

Every Nexus boss drops one EPIC crown at its ruins (purple ping + "EPIC DROP" message), replacing the old random items:

| Boss | Item | Bonus |
|---|---|---|
| Lane boss (Level 1) | Champion's Crown | +200 Str/Agi/Int |
| Level 2 boss | Dark Crown | +400 |
| Level 3 boss | Frozen Crown | +600 |
| Level 4 boss | Shadow Crown | +800 |
| Level 5 boss | Inferno Crown | +1000 |

## Champions (v4.3, Jiří: twelve champions of X Hero Siege 3.28, as they are there)

Their abilities are the game's own native abilities with the numbers of X Hero Siege 3.28 (Sogat, 2007). `gen/xhs_data.py` holds them, generated from the owner's local copy of that map by `tools/xhs_port.py`, which also checks them against it. The map itself is not in this repo. The text a player reads is ours (`gen/xhs_text.py`).

| Tavern | Champion | Q | W | E | R (ultimate, 2 levels; the Dryad's has 4) | T | D (innate) | F (hero level 20) |
|---|---|---|---|---|---|---|---|---|
| Q | **Dryad** | Evasion | **Multiple Arrows** | Critical Arrows | Trueshot Aura | Endurance Aura | Envenomed Spears | Spell Immunity |
| W | **Mountain King** | Storm Bolt | Thunder Clap | Bash | Avatar | Muradin's Hammer | Thunder Spirit | Lightning Shield |
| E | **Tauren Chieftain** | Shockwave | War Stomp | Pulverize | Lightning Stroke | Endurance Aura | Battle Roar | Reincarnation + a stronger Roar |
| R | **Pit Lord** | Rain of Fire | War Stomp | Cleaving Attack | Doom | Unholy Aura | Howl of Terror | Finger of Death |
| A | **Archmage** | Blizzard | Water Elemental | Frost Bolt | Starfall | Debilitation Aura | Anti-magic Shield | Water Shield |
| S | **Lich** | Frost Nova | Breath of Frost | Frost Arrows | Frost Beast | Frost Armor | Frost Frenzy | Frost Chaos |
| D | **Paladin** | Healing Wave | Howl of Weakness | Fan of Light | Pure Light | Devotion Aura | Taunt | Light Frenzy |
| F | **Blademaster** | Wind Walk | Critical Strike | Mirror Image | Bladestorm | War Drums | Berserk | Partition |
| Z | **Beastmaster** | Summon Bear | Feral Spirit | Summon Hawk | Stampede | Thorns Aura | Spirit Pig | Terror Wolf |
| X | **Crypt Lord** | Impale | Spiked Carapace | Carrion Beetles | Locust Swarm | Poison Sting | Anub'arak's Claw | Burrow Impale |
| C | **Demon Hunter** | Immolation | Negative Energy | Evasion | Metamorphosis | Vampiric Aura | Roar | Resistant Skin |
| V | **Priestess of the Moon** | Chain Lightning | Watery Minion | Forked Lightning | Monsoon | Trueshot Aura | Rejuvenation | Lightning Chaos |

- **Tooltips (v4.4, Jiří: real effects, real numbers, all ranks; `gen/xhs_tips.py`):** generated from the numbers the ability really has. The title says the rank, every value that changes shows all ranks side by side: the current one in gold, learned ones light grey, future ones grey. Values that stay the same stand in one line. The last line says the next rank and its hero level in orange, or Max rank in green. The Learn card has one text for all ranks in the engine: it lists them all in white and names the offered rank in its title. A switch (Immolation, Lightning Shield) says that it is on and how to stop it. Autocast keeps the game's own right-click lines. The innate ability and the tavern name what comes at hero level 20. A text must stay under 900 bytes.
- **Known limit, from the reference: at hero level 20, before the skills are at max rank, 13 functions meet 12 buttons.** Move, Stop, Hold, Attack, Patrol, D, T, Q, W, E, R, F and the Learn button. The engine leaves one out, and which one depends on the champion. Seen in hidden pictures of all 12 places, five skills at rank 1, then level 20: the Lich has no button for Frost Chaos (F), the Mountain King keeps Lightning Shield on another place and loses Muradin's Hammer's tooltip (T, a passive), the Demon Hunter loses Resistant Skin's tooltip (F, a passive). The other nine were not looked at. **The way out:** bring all five skills to their max rank (18 points, the Dryad's 20): the Learn button goes, also with points left, and all buttons stand in their places. A passive works without its button. The reference has no card override of its own either.
- **Card:** Q W E R on the bottom row, D and T above them, F where the Learn button is once every skill is learned (the reference's layout). Every button is reachable once the skills are at max rank: see the known limit above.
- **The Dryad's Multiple Arrows, measured:** the spears come **with her attack**, at different enemies, landing within about 0.1 s. Enemies hit per attack, her own hit included: **4 / 6 / 8 / up to 10** at levels 1 to 4 (12 enemies around her; at level 4 it was 8 to 10). Faster attacks mean more volleys: one every 0.97 s, with +200 Agility one every 0.37 s. A spear does the damage of **her weapon** (43 to 51; 223 to 230 with +200 Agility): the native ability ignores its 250 / 500 / 1000 / 2000 fields. On one lone enemy one hit; holding position with nobody in reach none; stop orders add nothing. These are the game's own rules for this ability, kept as they are.
- **Doom, level 2:** takes monsters up to level 5 like level 1 does, thanks to one changed cell in the game's ability table that the map carries (gotchas). 500 / 1000 damage per second, 1 / 2 Doom Guards at its target's death.
- **Level 20** (`HeroGrants`): the F ability, also when a level-up jumps past 20. The Tauren's old Roar makes room for the new one.
- **The few triggers they need** (`OnHeroGlue*`), from the reference: from level 20 the Mountain King's Thunder Clap and Storm Bolt and, with Roar on, the Tauren's War Stomp and Shockwave strike twice; Light Frenzy resets its target's cooldowns; each level of War Drums swaps in the real aura.
- **Different from the reference, on purpose:** our max hero level is 1000 (there 30), and from level 21 every level-up adds +30 to all stats (`ATTR_*`), because the old Attributes skill no longer fits: a hero has at most 5 learnable abilities. Their gameplay constants stay ours (armor per Agility and so on, the shops depend on them) except the speed cap, see the bosses. Natives our bosses also use got their own ids (`XHS_REMAP`), so their numbers stay apart.
- **Not in the reference, not here:** the Far Seer, who was a champion until v4.2. The Priestess takes his lightning role.
- Spells on **Q W E R T**, innate on **D**, level 20 on **F**. Death → revive on the Champion's Circle after `4 + 2*level` s, max 24 s (`StartRevive`), not if Reincarnation has already brought him back. Deaths counted.
- **Partition and Terror Wolf:** the hero is hidden while the summoned form fights. It buys and collects as usual; if all forms die he dies and revives.
- **Level 2** when the player's first wave is cleared (or at his wave 2). Every level-up refills HP + mana.

## Champion's Circle shop (per player, `KINDS_DEF` rows 1–3 in `gen/objects.py`)

| Slot | Key | Item | Gives | Base price |
|---|---|---|---|---|
| 1,1 | Q | Health | +600 max HP | 100 |
| 2,1 | W | Mana | +75 max mana | 100 |
| 3,1 | E | Damage | +20 damage | 100 |
| 4,1 | R | Armor | +8 armor | 100 |
| 1,2 | A | Strength | +20 Str | 100 |
| 2,2 | S | Agility | +20 Agi | 100 |
| 3,2 | D | Intelligence | +20 Int | 100 |
| 4,2 | F | All stats | +10 Str/Agi/Int | 100 |
| 1,3 | Z | Experience | +1 level: XP = 100 × (level + 1), the game's NeedHeroXP step (kind type 2, `AdvanceStatPrice`) | 250 |

- **Why these values (v4.1):** a buy of a stat gives Strength +500 HP, Agility +6 armor and +40 % attack speed, and the primary stat also +20 damage. Health and Armor give more of their one thing than the stat that also gives it, so a champion who does not need the stat's other half has a real choice from the first coin. Damage equals a primary stat's damage without its side effects: for a Strength or Agility champion his primary stat stays better until its price has risen. Mana and off-primary Intelligence still give nothing a champion can use (every skill is passive).
- Instant: each buy adds a hidden item-bonus ability copy → shows as a **green +N**, base stats untouched.
- Every buy +5 % for that player and kind (`STAT_PRICE_GROWTH` 1.05, v4.4; compound and rounded: 100, 105, 110, 116 ... step 99 costs 12 524), 100 steps (`STAT_TIERS`, the most 2-digit ids
  allow; the script indexes `kind * gKindStride (128) + step`). The buy counts **at once**,
  also while the champion is dead (`GrabTick` → `GrabDeadEnum` counts tomes at the circle / in the dead champion's
  inventory); the bonus is handed over when he is alive (`ApplyBought`: `gStatApplied` per kind, `gXpPending`).
- Tooltip: `Agility  Lv 3  (S)` (Lv = times bought, light blue) / `+20 Agility` / orange `Next buy: +5% gold`.
- Icons: game's own hero-attribute icons for Str/Agi/Int (`gen/icons.py`), Heal / Brilliance / Attack /
  Defend / StatUp for the rest.

## Castle (`hcd0`): 8000 HP, armor 10 — and the castle shop

Select the castle and buy with a champion anywhere on the plaza (3400 radius, `CASTLE_SHOP_RANGE`). Every castle buy costs
**1 tree** (`CASTLE_TREE_COST`), no gold. Everyone sees "Name: +3 castle armor".

| Key | Buy | Effect |
|---|---|---|
| Q | Castle Health | +1000 max HP (stacks) |
| W | Castle Armor | +3 armor (stacks) |
| E | Castle Regeneration +N HP/s | +10 HP per second (stacks). The button names what was bought (N), and its own +5 HP/s comes on top: every step is its own item type |
| R | Repair Castle | +2000 HP heal (repeatable) |
| A | Shockwave | 25 % of their max HP to every wave monster within 1100 of the castle; a boss takes 300 + 30 × the highest wave of any lane (repeatable) |

Stacking upgrades use one hidden ability per buy (global counter, 100 max). Works while the buyer's champion is
dead. A restart replaces the castle, so upgrades reset. The castle deals no damage on its own.
⚠️ The castle is owned by the neutral-extra player (15); its shop carries both a neutral-building (`Xcsh`, `Aneu`)
and an allied shop-sharing (`Xcs2`, `Aall`) buyer ability — the `Aall`-only version could not be used in-game.

## Secret grove (narrow passage at the SE plaza corner)

The grove shops sell **remotely**: select a shop (e.g. jump there via the minimap) and buy — your champion can be
anywhere on the map (`Aneu` radius 20 000). Bought items go straight into his inventory.

- **Fountain of Power**: 2 % max HP + 2 % max mana per second.
- **Bank**: trees → passive income (see above).
- **Premium Armory** — 8 simple items, **1000 gold** each (`PREMIUM_DEF`), hotkeys
  Q W E R / A S D F, stock 5 (`PREMIUM_STOCK`, restock 30 s) so rank 5 can be bought in one go. **Five ranks:** buying an item you already hold merges both into the next rank
  (`MergePremium`: two items of one family in an inventory become one at the summed level, checked on buy, on
  pickup and every 0.2 s from `GrabTick`); ranks above 5 are refunded. **v4.4 (Jiří: grossly overtuned), the bonus of a rank in all, not on top of the one before.** Modest starter values, the highest in line with parts of X Hero Siege's own far dearer items or the native item they copy. Not a measured economy:

  | Item | Rank 1 / 2 / 3 / 4 / 5 | Up to v4.3 |
  |---|---|---|
  | Vampire Fang | 5 / 10 / 15 / 20 / 30 % lifesteal | 30 to 70 % |
  | Fury Gloves | +5 / 10 / 15 / 20 / 25 % attack speed | +40 to +100 % |
  | Executioner's Axe | 4 / 8 / 12 / 16 / 20 % chance of 2× damage | 20 to 40 %, 3× |
  | Stormhammer | 3 / 6 / 9 / 12 / 15 %, +5 / 10 / 15 / 20 / 25 damage, 0.5 s stun | 20 to 40 %, +40 to +120, 1 s |
  | Phantom Cloak | 3 / 6 / 9 / 12 / 15 % dodge | 25 to 45 % |
  | Winged Boots | +10 / 20 / 30 / 40 / 50 move speed | +100 to +200 |
  | Troll Heart | +2 / 4 / 6 / 8 / 10 HP/s | +15 to +55 |
  | Arcane Mask | +10 / 20 / 30 / 40 / 50 % mana regeneration | +150 to +350 % |

  Each rank is its own item type, so its tooltip shows every rank with this one in gold, and no player's state.

- **Long Reach** — **not sold since v2.6**, when the Dryad was the only champion. Melee champions came later and it was not brought back. The code stays (`REACH_*`,
  `TryReach`: +150 attack range once, melee champions only, ranged buyers refunded).
- **Apothecary** (`SHOPS["apothecary"]`, stock 8, restock 10 s): potions are sold as **power-up tokens** `Ipo1`–`Ipo4`
  (`POTION_TOKENS`; a power-up is sold even to a full inventory, a normal item is refused). A token adds **one charge**
  to the potion the champion carries, or puts the potion into a free slot, or refunds when the inventory is full and
  holds no such potion (`GivePotion`, from `OnItemSold` / `OnItemPickup`). Potions heal a **percent** of max, fixed price, and
  **stack** in the inventory (one slot, more charges) — `POTIONS`, script `PotionIndex` / `StackPotion` (on buy and
  pickup) / `MergePotions` (every 0.2 s from `GrabTick`: same-type potions in two slots merge into the first) / `DrinkPotion` (on use; the native fixed heal of `AIh1`/`AIm1`/`AIre` is zeroed):
  Healing Potion 50 % HP 100 gold (10 s cooldown), Mana Potion 50 % mana 100 gold (10 s), Restoration Potion
  100 % HP + mana 250 gold (30 s), Invulnerability Potion 200 gold. Also boots, rings, periapt, staff of teleportation.

## Enemy bases and bosses (`gen/objects.py`)

- Every tower and Nexus is classed **Mechanical** (`NO_LIFESTEAL`): WarCraft lifesteal does not work against
  mechanical targets, so champions cannot heal off them.

- **v3.9 (Jiří): every tower and Nexus damage ×10, HP ×5; bosses HP ×10, damage ×50.** Every next building hits
  harder: Level 1 tower < Level 1 Nexus (~10 % more than its tower) < Level 2 tower < … < Level 5 Nexus
  (`building_ladder`, asserted at build time).
- Tower: **20 000 HP**, armor 4, **~25 000 chaos** (24995 + 1d10) / 1.3 s, range 750 — mid-lane (`tower_pos`, v = 3600,
  1776 from the Champion's Circle), far in front of the Nexus (v = 5440) so their ranges never overlap: tower first,
  then its stronger waves, then the Nexus.
- **Nexus: 15 000 HP, armor 10, huge attack** ~27 500 (27400 + 4d50) chaos missile every 2.5 s, range 700, hits air too
  (`BASE_HP`, `NEXUS_*`, `nexus_attack`).
- **Tower Warden** (v4.4, Jiří: "where the turret lay, a boss must spawn", `OnTowerDestroyed`, `gProtector[L]`, tier 0): rises on the tower's ruins, base 35 000 HP (52 500 with its Heart of Ruin), armor 3, ~1800 chaos per hit (`BOSS_HP[0]`, `BOSS_DMG[0]`; a gate's × its level). Its own unit, gear, spells, cooldowns and leash (`BossBrain`, 1500 from the ruins, `WARDEN_LEASH`). It stands beside the later Nexus boss, does not block the Nexus, drops no crown and pays 150 gold (a gate half of its gold). It fights alone, without adds.
- Lane boss: **tier 1**, base 60 000 HP (120 000 with its Heart of Ruin), armor 4, ~2400 chaos per hit (`BOSS_HP[1]`, `BOSS_DMG[1]`; tier 2 exists in the data but is unused).
- **Their gear (v4.4, Jiří: still far too easy, brutal real equipment, `BOSS_GEAR`, `BossEquip`):** three real items in a real inventory, bound (no drop, no pawn, not in `DropEpic`), with the native item abilities:

  | Item | Tower Warden | Nexus and gate boss |
  |---|---|---|
  | Heart of Ruin | +50 % of its base HP | +100 % of its base HP, before the wave's and team's factors |
  | Executioner Gauntlets | +50 % attack speed, 20 % chance of 2× | +100 % attack speed, 25 % chance of 2× |
  | Runic Warplate | +25 armor, 20 % less spell damage (`AIsr`) | +40 armor, 25 % less spell damage |

  No lifesteal, no regeneration, no invulnerability.
- **Bosses since v4.3 (Jiří: far too easy; ultra fast, high damage, durable, no stun):**
  - **As strong as their lane's wave when they rise** (`BossEquip`), n = wave − 1: HP × (1 + 0.02 n²), at most ×16, damage × (1 + 0.008 n²), at most ×8; gate bosses also × the team in HP. Lane boss at wave 20: 986 400 HP with its Heart of Ruin, 9335 a hit. Tower Warden at wave 10: 137 500 HP.
  - **Speed 522, the engine's top** (`BOSS_SPEED`; the map's `MaxUnitSpeed` is raised from 400 for it, so a hero's speed auras can reach further too), an attack every second.
  - **No stun holds them** (`StunStrip`, the final boss's rule for all): the stun buffs come off at once, damage and slows stay. Impale throws one up for its second and its damage lands; the rest of its stun comes off then.
  - **Their own spells** (`BOSS_SPELLS`, `Xb**`, 10 levels, level 1 + wave / 5 + the gate's level, 1200 damage per level on one target), so the champions' copies of the same spell stay faithful. Spells are due every 7 and 11 s, and adds every 25 s (`BossTick`; since v4.3 they really come, the old schedule could never reach them) with the wave's strength.
  - **How they cast (v4.4, `BossBrain`):** their own orders leave a running Blizzard or Rain of Fire alone, except the leash; the engine or the fight can still end it. A spell the game refuses stays due, adds come on time also during a channel. A spell-immune target gets no spell, real attacks instead. Spells keep the native's cooldown at every level.
  - Leashed to their ruins at 1600. They ignore invulnerable targets.

## UI and commands

- **Scoreboard** (top right, 1 s refresh): title `m:ss    Castle HP / max HP` (game time from the end of
  champion select, stops at the end; max HP includes Castle Health upgrades). Columns: Player · Lv · Wave (his lane's, `done` when its boss is dead) · Kills · Deaths ·
  Income (bank gold per minute). An opened gate adds a row, `Level 2` with its wave. The end dialog shows the time ("VICTORY in 23:45!").
- **-help** (only to the asker): gold `Commands`, then light-blue command + grey description per line:
  `-zoom 250` zoom out · `-cam` camera follows your hero · `Space` jump to your hero · `-break 60` · `-wave 5`.
- **Pace settings** (any player, announced to all; `OnConfigChat`): `-break N` = shopping-break length (5–300 s,
  default 60), `-wave N` = seconds between waves (0–60 s, default 0), both for every lane. No number = show the current values.
  A lane's countdown already running is shortened at once if it is longer than the new value; kept across *Play again*.
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
