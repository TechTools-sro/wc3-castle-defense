# Balance

What was asked, the rule, and what was really measured. The rules and exact numbers live in [gameplay.md](gameplay.md), the code in
`WAVE_*` of `gen/objects.py` and `Scale*` of `gen/castle_logic.j`.

Jiří, 2026-11-01: stronger monsters and smart scaling, so that a level 1 champion struggles, winning is not trivial, and players think
about upgrades and cooperate.

## The rule (v4.1)

| What | Rule |
|---|---|
| Wave 1 | Melee 700 HP / 60 damage, ranged 420 HP / 120 damage. v4.0 had 200 / 30 and 120 / 60 |
| Every wave | With n = wave − 1: HP × (1 + 0.03 n²), damage × (1 + 0.018 n²). HP grows faster. v4.0 added only units |
| Lane stage | Tower down: HP ×1.5, damage ×1.25. Nexus down: HP ×2, damage ×1.5. v4.0: ×2 and ×3 for both |
| Factions | Same combat values, only the model and its movement type differ. In v4.0 the inherited attack type, speed, armor and spells differed |
| Personal lanes | Do not scale with players: each player already adds a lane |
| Shared gates | HP × (1 + 0.35 (team − 1)), for gate monsters, Protectors, towers, Nexuses and bosses. Damage does not depend on the team |
| Team | The players at the start of the round. Leaving lowers nothing, because the others control that champion |
| Rescaling | Never heals: the actual HP stays. The final boss too: v4.0 kept his percentage, which gave him free HP every minute |
| Bank | At most 120 counted seconds of income per wave, renewed only by the next wave; always during the final boss |
| Shop | Health +600, Damage +20, Armor +8 (were +100, +5, +2), so that they compete with the stats that also give them |
| Unchanged | The base stats of towers, Nexuses and bosses (their HP now also grows with the team, see Shared gates), the final boss's clock growth, wave sizes, kill and wave gold, prices |

## Three kinds of evidence, never mixed

1. **The model** (`tools/balance_matrix.py [--rev REV]`): formulas over the game's real tables. No pathing, healing or potions; a fixed number of attackers and targets. It shows trends and compares champions. Its loadouts and budgets are not the bot's, so it does not predict a real fight.
2. **Real fights** (`tools/balance_probe.py`): the production game, hidden, played by a simple bot with ordinary orders and real purchases. A bot is not a player.
3. **The self-test** (`tools/test_env.py run`): mechanical regression. It gives itself gold and levels, pauses enemies and forces kills, so it says nothing about balance. It does check the rules: a scale applied twice changes nothing, a wounded unit that grows does not heal, the shared HP for 1, 2, 4 and 8 players (a simulated count on real units), a player who picked and left (a simulated state), the real first wave after a restart, and the Bank's budget and kill rule. **97 PASS, 0 FAIL** (`wip-selftest-3`, map `3532ceed…`). The release differs from that map only in text: the version, comments and two Bank tooltips.

## Real fights

Seed 1, a solo lane on the Scourge arm, ordinary orders, production timings, normal 1000 gold, legal purchases. The same bot played v4.0 and v4.1, and during a measured fight nothing changes HP, gold, level or time. **Every run had 0 tower and Nexus hits**, so these are monster fights only. A failed fight stays in the data.

Three loadouts, bought before wave 1 and frozen for the 180 s of the run: **starter** = All ×4, Agi ×2, Str ×2, potion (924 g); **primary** = primary stat ×8, potion (989 g); **careless** = Mana ×4, Damage ×4 (836 g).

### Frozen loadouts: 180 s

Wave = the last wave **reached**, not cleared.

| Champion | Loadout | v4.0 wave / deaths / castle | v4.1 wave / deaths / castle |
|---|---|---|---|
| Dryad | starter | 10 / 0 / 8000 | 5 / 1 / 7547 |
| Dryad | primary | 10 / 0 / 8000 | 6 / 3 / 1413 |
| Dryad | careless | 3 / 5 / 7491 | 2 / 8 / 4233 |
| Mountain King | starter | 10 / 0 / 8000 | 6 / 2 / 4635 |
| Mountain King | primary | 10 / 0 / 8000 | 5 / 2 / 5906 |
| Mountain King | careless | 4 / 5 / 7060 | 2 / 8 / 768 |
| Archmage | starter | 10 / 0 / 8000 | 6 / 2 / 4955 |
| Archmage | primary | 10 / 0 / 8000 | 5 / 7 / 4053 |
| Archmage | careless | 6 / 5 / 7406 | 4 / 7 / 4098 |

### Frozen loadouts: wave 1

First hit and clear in seconds after the spawn. **Min HP** = the lowest HP in the wave, **taken** = all damage received, which can be more than the HP lost. Dealt = HP removed from monsters by the champion.

| Champion | Loadout | HP | v4.0 first hit / clear / min HP / taken / dealt | v4.1 first hit / clear / min HP / taken / dealt |
|---|---|---|---|---|
| Dryad | starter | 2550 | 4.8 / 11 / 2479 / 101 / 1313 | 4.8 / 26 / 1239 / 1419 / 4596 |
| Dryad | primary | 550 | 6.1 / 8 / 542 / 7 / 1316 | 4.8 / 13 / 252 / 307 / 4607 |
| Dryad | careless | 550 | 4.8 / 42 / 0 / 1006 / 1307, 1 deaths | 4.8 / 92 / 0 / 2945 / 4597, 5 deaths |
| Mountain King | starter | 2700 | 4.4 / 12 / 2618 / 116 / 1366 | 4.4 / 22 / 1466 / 1326 / 4747 |
| Mountain King | primary | 4700 | 4.4 / 14 / 4410 / 369 / 1391 | 4.4 / 28 / 1825 / 4007 / 4688 |
| Mountain King | careless | 700 | 4.4 / 32 / 0 / 1001 / 1345, 1 deaths | 4.4 / 89 / 0 / 4323 / 4657, 5 deaths |
| Archmage | starter | 2450 | 4.8 / 11 / 2370 / 102 / 1323 | 4.8 / 22 / 1316 / 1256 / 4652 |
| Archmage | primary | 450 | 4.8 / 11 / 277 / 177 / 1349 | 4.8 / 23 / 0 / 961 / 4619, 1 deaths |
| Archmage | careless | 450 | 4.8 / 24 / 0 / 480 / 1344, 1 deaths | 4.8 / 40 / 0 / 1214 / 4641, 2 deaths |

### Frozen loadouts: waves 2, 3, 5

Each cell: seconds in the wave, min HP / the loadout's HP before wave 1. That second number stays the same in every wave. Every level-up raises max HP and refills HP, so min HP can pass it and can rise from wave to wave without a purchase.

| Champion | Loadout | Wave | v4.0 | v4.1 |
|---|---|---|---|---|
| Dryad | starter | 2 | 12 s, 2494 / 2550 | 33 s, 1010 / 2550 |
| Dryad | starter | 3 | 14 s, 2480 / 2550 | 33 s, 212 / 2550 |
| Dryad | starter | 5 | 12 s, 2554 / 2550 | 8 s (open at the end), 656 / 2550 |
| Dryad | primary | 2 | 10 s, 529 / 550 | 17 s, 188 / 550 |
| Dryad | primary | 3 | 10 s, 530 / 550 | 18 s, 34 / 550 |
| Dryad | primary | 5 | 9 s, 641 / 550 | 36 s, 0 / 550, 1 deaths |
| Dryad | careless | 2 | 61 s, 0 / 550, 2 deaths | 57 s (open at the end), 0 / 550, 3 deaths |
| Dryad | careless | 3 | 47 s (open at the end), 0 / 550, 2 deaths | - |
| Mountain King | starter | 2 | 12 s, 2674 / 2700 | 22 s, 1383 / 2700 |
| Mountain King | starter | 3 | 13 s, 2659 / 2700 | 22 s, 1096 / 2700 |
| Mountain King | starter | 5 | 12 s, 2849 / 2700 | 39 s, 0 / 2700, 1 deaths |
| Mountain King | primary | 2 | 14 s, 4511 / 4700 | 27 s, 522 / 4700 |
| Mountain King | primary | 3 | 16 s, 4481 / 4700 | 42 s, 0 / 4700, 1 deaths |
| Mountain King | primary | 5 | 8 s, 4519 / 4700 | 11 s (open at the end), 1191 / 4700 |
| Mountain King | careless | 2 | 35 s, 0 / 700, 1 deaths | 60 s (open at the end), 0 / 700, 3 deaths |
| Mountain King | careless | 3 | 39 s, 0 / 700, 1 deaths | - |
| Archmage | starter | 2 | 11 s, 2386 / 2450 | 22 s, 962 / 2450 |
| Archmage | starter | 3 | 12 s, 2385 / 2450 | 20 s, 1192 / 2450 |
| Archmage | starter | 5 | 12 s, 2515 / 2450 | 43 s, 0 / 2450, 1 deaths |
| Archmage | primary | 2 | 11 s, 329 / 450 | 26 s, 0 / 450, 1 deaths |
| Archmage | primary | 3 | 12 s, 285 / 450 | 53 s, 0 / 450, 3 deaths |
| Archmage | primary | 5 | 10 s, 465 / 450 | 1 s (open at the end), 160 / 450 |
| Archmage | careless | 2 | 29 s, 0 / 450, 1 deaths | 57 s, 0 / 450, 3 deaths |
| Archmage | careless | 3 | 27 s, 0 / 450, 1 deaths | 45 s, 0 / 450, 2 deaths |
| Archmage | careless | 5 | 34 s, 0 / 450, 1 deaths | - |

### Playing on: 420 s

Starter, then every coin into All, All, Agi, Str and every tree into the Bank. Stage 0 only: the bot does not push. Cell: seconds in the wave, HP taken, min HP, level, gold spent. `-` = not reached.

| Champion | Waves reached, deaths: v4.0 | v4.1 |
|---|---|---|
| Dryad | 20, 0 | 16, 0 |
| Mountain King | 21, 0 | 20, 0 |
| Archmage | 24, 0 | 20, 0 |

| Champion | Wave | v4.0 | v4.1 |
|---|---|---|---|
| Dryad | 1 | 11 s, 101, 2479, L2, 924 g | 26 s, 1419, 1239, L2, 924 g |
| Dryad | 3 | 12 s, 111, 2760, L3, 1484 g | 23 s, 1574, 1380, L3, 1365 g |
| Dryad | 5 | 10 s, 27, 4650, L5, 2082 g | 20 s, 1363, 3840, L5, 2308 g |
| Dryad | 10 | 11 s, 162, 10875, L10, 5904 g | 21 s, 1461, 10025, L10, 6932 g |
| Dryad | 15 | 14 s, 12, 20600, L14, 14033 g | 22 s, 1206, 21289, L14, 15107 g |
| Dryad | 20 | 18 s, 9, 29298, L18, 27110 g | - |
| Mountain King | 1 | 12 s, 116, 2618, L2, 924 g | 22 s, 1326, 1466, L2, 924 g |
| Mountain King | 3 | 8 s, 100, 2945, L3, 1484 g | 18 s, 958, 2295, L3, 1365 g |
| Mountain King | 5 | 7 s, 27, 4914, L5, 2082 g | 11 s, 616, 3941, L5, 2082 g |
| Mountain King | 10 | 18 s, 169, 11225, L10, 5904 g | 11 s, 426, 10257, L10, 5904 g |
| Mountain King | 15 | 11 s, 24, 21596, L14, 14033 g | 13 s, 448, 21506, L14, 14379 g |
| Mountain King | 20 | 20 s, 156, 30150, L18, 25678 g | 19 s, 549, 30311, L18, 25914 g |
| Archmage | 1 | 11 s, 102, 2370, L2, 924 g | 22 s, 1256, 1316, L2, 924 g |
| Archmage | 3 | 8 s, 29, 2699, L3, 1259 g | 16 s, 642, 2110, L3, 1365 g |
| Archmage | 5 | 9 s, 7, 4567, L5, 2082 g | 14 s, 690, 3539, L5, 1952 g |
| Archmage | 10 | 10 s, 7, 9750, L10, 5444 g | 18 s, 659, 9916, L10, 6377 g |
| Archmage | 15 | 12 s, 0, 19475, L14, 13852 g | 15 s, 292, 21225, L14, 14921 g |
| Archmage | 20 | 12 s, 141, 28400, L18, 24870 g | 19 s, 470, 30071, L18, 25914 g |

The gold columns are close but not certified: these maps predate the probe's purchase accounting, so a Bank purchase can show as failed although the income rose, and a purchase still pending at the end is unknown. Combat numbers and confirmed purchases are not affected.

### Holding a wave back for the Bank

Dryad, starter, no further purchases, income 200. From wave 3 she walks away from the last monsters and stays away.

| | v4.0 | v4.1 |
|---|---|---|
| Wave 3 stood | from 54 s to the end at 420 s, 3 monsters | from 90 s to the defeat at 231.7 s, 4 monsters |
| Payments of +200 in that wave | 6 (120 s … 420 s), no end in sight | 2 (120 s, 180 s), then the game was over |
| Castle | 8000 → 4960 at 390 s, about 10 HP per second | 8000 → 0, about 90 HP per second, **destroyed at 231.7 s** |

This real run shows two things: v4.0 paid for as long as a wave stood, and in v4.1 the last monsters of a wave are dangerous to the castle. It does **not** show that a third payment is denied: the castle fell 8 s before the payment at 240 s. The cap of 120 counted seconds per wave, its reset by the next wave and the kill rule are shown by the self-test's mechanical checks of `BankTick` and by the code, not by this fight.

### Evidence

Under `~/games/wc3-test-env/evidence/`: `balance-v40-safe3-dryad` and `balance-v40-safe3` (v4.0), `balance-cand1` and `balance-cand1p` (v4.1), `balance-v40-stall1` and `balance-cand1s3` (the Bank). All passed the log validation. Earlier batches (`balance-calib-v40-bot-limiter`, `balance-safe3-calib`, `balance-v40-safe2`, `balance-cand1s`, `balance-cand1s2`) are calibration of the bot or stalls that did not hold, and are not in the tables. Jiří's own game started during `archmage-progress` of `balance-cand1p` and both Bank runs: they are separate games, but for those three runs the check of zero change in personal files could not apply.


## The model: seven champions, four factions

Budget = what a solo lane has when that wave starts. All of it goes to the build's cycle. **Mixed** = All, All, Str, Agi repeated. **Primary** = the primary stat only. **Hybrid** = primary, Health, Armor. **Tank** = Health, Armor. **Careless** = Mana, Damage. Each cell: share of HP lost clearing the wave / seconds to clear it, on stage 0. Factions no longer differ in v4.1; v4.0 cells are the range over the four factions.

**Wave 1** (budget 1000 g, model level 1, 7 monsters per lane)

| champion | mixed v4.0 | mixed v4.1 | primary v4.0 | primary v4.1 | careless v4.0 | careless v4.1 | hybrid v4.1 | tank v4.1 |
|---|---|---|---|---|---|---|---|---|
| Dryad | 3-5 % / 4 s | 36 % / 17 s | 5-7 % / 2 s | 55 % / 7 s | 235-331 % / 26-27 s | 1081 % / 43 s | 54 % / 28 s | 266 % / 176 s |
| Mountain King | 2-3 % / 3 s | 23 % / 11 s | 5-7 % / 4 s | 54 % / 17 s | 128-179 % / 16 s | 620 % / 29 s | 58 % / 36 s | 156 % / 105 s |
| Tauren Chieftain | 2-3 % / 2 s | 20 % / 10 s | 5-6 % / 4 s | 48 % / 15 s | 110-155 % / 14 s | 541 % / 26 s | 52 % / 32 s | 136 % / 91 s |
| Pit Lord | 2 % / 2 s | 17 % / 8 s | 4-5 % / 3 s | 41 % / 13 s | 89-125 % / 12 s | 442 % / 22 s | 44 % / 27 s | 112 % / 76 s |
| Archmage | 3-4 % / 4 s | 30 % / 14 s | 38-54 % / 3 s | 404 % / 13 s | 159-224 % / 14 s | 714 % / 23 s | 80 % / 28 s | 154 % / 98 s |
| Lich | 2-3 % / 3 s | 26 % / 12 s | 34-48 % / 3 s | 358 % / 11 s | 139-196 % / 12 s | 631 % / 20 s | 72 % / 25 s | 134 % / 84 s |
| Far Seer | 3-4 % / 3 s | 29 % / 13 s | 35-49 % / 3 s | 367 % / 12 s | 145-204 % / 13 s | 650 % / 22 s | 76 % / 27 s | 148 % / 95 s |

**Wave 5** (budget 1830 g, model level 4, 19 monsters per lane)

| champion | mixed v4.0 | mixed v4.1 | primary v4.0 | primary v4.1 | careless v4.0 | careless v4.1 | hybrid v4.1 | tank v4.1 |
|---|---|---|---|---|---|---|---|---|
| Dryad | 1-2 % / 2 s | 28 % / 14 s | 3-4 % / 2 s | 74 % / 8 s | 219-273 % / 20-21 s | 1762 % / 40 s | 33 % / 21 s | 352 % / 252 s |
| Mountain King | 1 % / 2 s | 20 % / 10 s | 4-5 % / 4 s | 83 % / 20 s | 131-163 % / 15 s | 1138 % / 33 s | 59 % / 41 s | 222 % / 163 s |
| Tauren Chieftain | 1 % / 2 s | 18 % / 9 s | 3-4 % / 3 s | 74 % / 18 s | 111-138 % / 13 s | 976 % / 29 s | 52 % / 36 s | 189 % / 139 s |
| Pit Lord | 1 % / 1 s | 14 % / 7 s | 3-4 % / 3 s | 63 % / 16 s | 92-115 % / 11 s | 816 % / 25 s | 44 % / 31 s | 158 % / 117 s |
| Archmage | 2 % / 3 s | 33 % / 16 s | 43-54 % / 3 s | 942 % / 17 s | 184-230 % / 13 s | 1525 % / 28 s | 92 % / 35 s | 233 % / 162 s |
| Lich | 1 % / 2 s | 25 % / 12 s | 36-45 % / 3 s | 785 % / 15 s | 151-189 % / 11 s | 1268 % / 24 s | 78 % / 30 s | 191 % / 132 s |
| Far Seer | 1-2 % / 3 s | 31 % / 15 s | 37-47 % / 3 s | 812 % / 16 s | 160-200 % / 13 s | 1316 % / 26 s | 84 % / 33 s | 219 % / 154 s |

**Wave 10** (budget 4735 g, model level 8, 35 monsters per lane)

| champion | mixed v4.0 | mixed v4.1 | primary v4.0 | primary v4.1 | careless v4.0 | careless v4.1 | hybrid v4.1 | tank v4.1 |
|---|---|---|---|---|---|---|---|---|
| Dryad | 0 % / 1 s | 23 % / 16 s | 1-2 % / 1 s | 129 % / 10 s | 132-155 % / 10 s | 4222 % / 41 s | 26 % / 22 s | 486 % / 444 s |
| Mountain King | 0 % / 1 s | 18 % / 12 s | 1-2 % / 2 s | 142 % / 23 s | 80-95 % / 8 s | 2790 % / 35 s | 51 % / 47 s | 300 % / 280 s |
| Tauren Chieftain | 0 % / 1 s | 17 % / 12 s | 1-2 % / 2 s | 140 % / 22 s | 75-88 % / 8 s | 2628 % / 34 s | 50 % / 45 s | 280 % / 262 s |
| Pit Lord | 0 % / 1 s | 12 % / 8 s | 1 % / 2 s | 120 % / 19 s | 63-74 % / 7 s | 2212 % / 29 s | 42 % / 38 s | 234 % / 219 s |
| Archmage | 0 % / 2 s | 31 % / 20 s | 27-32 % / 2 s | 2731 % / 21 s | 125-147 % / 8 s | 4209 % / 33 s | 87 % / 44 s | 321 % / 288 s |
| Lich | 0 % / 1 s | 21 % / 14 s | 23-27 % / 2 s | 2340 % / 19 s | 105-124 % / 7 s | 3599 % / 29 s | 76 % / 38 s | 272 % / 243 s |
| Far Seer | 0 % / 2 s | 32 % / 21 s | 25-30 % / 2 s | 2554 % / 22 s | 118-139 % / 8 s | 3941 % / 34 s | 88 % / 45 s | 336 % / 303 s |

**Wave 20** (budget 19592 g, model level 17, 62 monsters per lane)

| champion | mixed v4.0 | mixed v4.1 | primary v4.0 | primary v4.1 | careless v4.0 | careless v4.1 | hybrid v4.1 | tank v4.1 |
|---|---|---|---|---|---|---|---|---|
| Dryad | 0 % / 0 s | 21 % / 16 s | 0 % / 0 s | 272 % / 13 s | 32-36 % / 2 s | 10027 % / 31 s | 20 % / 22 s | 614 % / 607 s |
| Mountain King | 0 % / 0 s | 16 % / 12 s | 0 % / 0 s | 254 % / 20 s | 19-21 % / 2 s | 6353 % / 27 s | 29 % / 33 s | 343 % / 345 s |
| Tauren Chieftain | 0 % / 0 s | 20 % / 16 s | 0 % / 1 s | 324 % / 25 s | 22-25 % / 3 s | 7687 % / 34 s | 36 % / 42 s | 412 % / 416 s |
| Pit Lord | 0 % / 0 s | 10 % / 8 s | 0 % / 0 s | 252 % / 19 s | 17-19 % / 2 s | 5902 % / 26 s | 27 % / 32 s | 308 % / 310 s |
| Archmage | 0 % / 0 s | 30 % / 23 s | 7-8 % / 0 s | 8067 % / 20 s | 33-37 % / 2 s | 11147 % / 28 s | 54 % / 34 s | 375 % / 367 s |
| Lich | 0 % / 0 s | 20 % / 15 s | 7-8 % / 0 s | 7793 % / 20 s | 32-36 % / 2 s | 10756 % / 28 s | 54 % / 34 s | 361 % / 353 s |
| Far Seer | 0 % / 1 s | 40 % / 30 s | 9-10 % / 1 s | 9648 % / 26 s | 40-45 % / 3 s | 13344 % / 37 s | 70 % / 45 s | 514 % / 504 s |

**Incoming DPS by faction** on the same mixed-build Dryad, stage 0.

v4.0:

| wave | The Scourge | The Burning Legion | The Tidal Horde | The Wildland Clans |
|---|---|---|---|---|
| 1 | 38 | 53 | 54 | 54 |
| 5 | 41 | 52 | 54 | 54 |
| 10 | 34 | 39 | 42 | 42 |
| 20 | 24 | 25 | 28 | 28 |

v4.1:

| wave | The Scourge | The Burning Legion | The Tidal Horde | The Wildland Clans |
|---|---|---|---|---|
| 1 | 108 | 108 | 108 | 108 |
| 5 | 171 | 171 | 171 | 171 |
| 10 | 283 | 283 | 283 | 283 |
| 20 | 630 | 630 | 630 | 630 |

**Stages, v4.1** (mixed build, a model).

| wave | champion | stage 0 | stage 1 | stage 2 |
|---|---|---|---|---|
| 10 | Dryad | 23 % / 15 s | 41 % / 22 s | 66 % / 29 s |
| 10 | Mountain King | 18 % / 12 s | 32 % / 18 s | 51 % / 23 s |
| 10 | Archmage | 31 % / 20 s | 56 % / 29 s | 88 % / 39 s |
| 20 | Dryad | 21 % / 16 s | 38 % / 24 s | 58 % / 31 s |
| 20 | Mountain King | 16 % / 12 s | 28 % / 18 s | 44 % / 24 s |
| 20 | Archmage | 30 % / 23 s | 54 % / 33 s | 83 % / 43 s |
| 30 | Dryad | 28 % / 22 s | 48 % / 32 s | 74 % / 41 s |
| 30 | Mountain King | 23 % / 19 s | 40 % / 27 s | 61 % / 35 s |
| 30 | Archmage | 44 % / 36 s | 77 % / 51 s | 119 % / 66 s |

**Late waves, v4.1** (mixed build, a model). The shop has 100 steps per stat, so HP stops growing near 78 000 while the monsters go on. A trend only: no real fight went past wave 24, and the model has no pathing or potions.

| wave | gold | level | Dryad | Dryad stage 2 | Mountain King | Mountain King stage 2 | Archmage | Archmage stage 2 | Far Seer | Far Seer stage 2 |
|---|---|---|---|---|---|---|---|---|---|---|
| 30 | 47082 | 24 | 28 % / 22 s | 74 % / 41 s | 23 % / 19 s | 61 % / 35 s | 44 % / 36 s | 119 % / 66 s | 59 % / 47 s | 158 % / 88 s |
| 40 | 85622 | 29 | 45 % / 33 s | 116 % / 59 s | 37 % / 28 s | 96 % / 50 s | 74 % / 54 s | 192 % / 97 s | 99 % / 72 s | 255 % / 129 s |
| 50 | 135232 | 34 | 54 % / 41 s | 134 % / 73 s | 45 % / 35 s | 112 % / 62 s | 114 % / 87 s | 286 % / 154 s | 152 % / 116 s | 381 % / 205 s |
| 60 | 195932 | 38 | 87 % / 56 s | 211 % / 96 s | 73 % / 48 s | 178 % / 82 s | 205 % / 130 s | 498 % / 225 s | 273 % / 174 s | 663 % / 301 s |
| 70 | 267742 | 42 | 173 % / 79 s | 408 % / 135 s | 145 % / 68 s | 344 % / 115 s | 404 % / 184 s | 956 % / 312 s | 538 % / 246 s | 1274 % / 417 s |

**Spending less, v4.1** (a model): the gold of that wave, but only a share of it spent.

| wave | champion | 100 % of the gold | 75 % of the gold | 50 % of the gold | 25 % of the gold |
|---|---|---|---|---|---|
| 5 | Dryad | 28 % / 14 s | 65 % / 21 s | 190 % / 36 s | 848 % / 74 s |
| 5 | Mountain King | 20 % / 10 s | 47 % / 16 s | 134 % / 26 s | 562 % / 53 s |
| 5 | Archmage | 33 % / 16 s | 75 % / 23 s | 210 % / 37 s | 858 % / 68 s |
| 10 | Dryad | 23 % / 15 s | 43 % / 19 s | 106 % / 26 s | 611 % / 59 s |
| 10 | Mountain King | 18 % / 12 s | 33 % / 15 s | 79 % / 20 s | 393 % / 40 s |
| 10 | Archmage | 31 % / 20 s | 56 % / 24 s | 135 % / 32 s | 667 % / 61 s |
| 20 | Dryad | 21 % / 16 s | 34 % / 19 s | 71 % / 25 s | 292 % / 40 s |
| 20 | Mountain King | 16 % / 12 s | 25 % / 15 s | 51 % / 18 s | 197 % / 28 s |
| 20 | Archmage | 30 % / 23 s | 48 % / 26 s | 98 % / 33 s | 368 % / 49 s |

**A shared gate wave with the whole team on it** (a model: a real team also holds its own lanes).

v4.0:

| wave | gate level | 1 players | 2 players | 4 players | 8 players |
|---|---|---|---|---|---|
| 15 | L2 | 2 s, 0 % | 1 s, 0 % | 0 s, 0 % | 0 s, 0 % |
| 15 | L5 | 8 s, 1 % | 4 s, 1 % | 2 s, 0 % | 1 s, 0 % |
| 25 | L2 | 1 s, 0 % | 0 s, 0 % | 0 s, 0 % | 0 s, 0 % |
| 25 | L5 | 3 s, 0 % | 2 s, 0 % | 1 s, 0 % | 0 s, 0 % |

v4.1:

| wave | gate level | 1 players | 2 players | 4 players | 8 players |
|---|---|---|---|---|---|
| 15 | L2 | 18 s, 24 % | 12 s, 16 % | 9 s, 12 % | 8 s, 10 % |
| 15 | L5 | 29 s, 49 % | 20 s, 33 % | 15 s, 25 % | 13 s, 21 % |
| 25 | L2 | 19 s, 24 % | 13 s, 16 % | 10 s, 12 % | 8 s, 10 % |
| 25 | L5 | 31 s, 48 % | 21 s, 32 % | 16 s, 25 % | 13 s, 21 % |

**First wave where the push targets can fall**, mixed build, 3 lives each: gold and level of that wave, as a bracket optimistic-cautious. Bounds of a model with all gold in stats, not a proven earliest wave. Personal targets do not depend on players.

v4.0:

| players | champion | Level 1 tower | Level 1 Nexus | Lane boss | L2 tower | L2 Nexus | L2 boss | L3 tower | L3 Nexus | L3 boss | L4 tower | L4 Nexus | L4 boss | L5 tower | L5 Nexus | L5 boss |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Dryad | 9 | 9 | 6 | 12 | 12 | 9 | 14 | 14 | 10 | 16 | 16 | 12 | 18 | 19 | 14 |
| 1 | Mountain King | 11 | 10 | 7 | 14 | 14 | 10 | 16 | 17 | 12 | 19 | 20 | 15 | 23 | 25 | 17 |
| 1 | Archmage | 13 | 11 | 8 | 16 | 15 | 12 | 19 | 19 | 14 | 22 | 24 | 16 | 27 | 32 | 19 |
| 2 | Dryad | 9 | 9 | 6 | 9-10 | 9-10 | 6-8 | 11-12 | 11-12 | 8-9 | 12-14 | 13-14 | 9-11 | 14-16 | 15-17 | 11-12 |
| 2 | Mountain King | 11 | 10 | 7 | 11-12 | 11-12 | 7-9 | 13-14 | 13-15 | 9-11 | 15-17 | 15-18 | 11-13 | 17-19 | 18-21 | 13-15 |
| 2 | Archmage | 13 | 11 | 8 | 12-14 | 12-14 | 9-10 | 14-16 | 14-16 | 10-12 | 16-19 | 17-20 | 13-14 | 19-22 | 20-25 | 14-17 |
| 4 | Dryad | 9 | 9 | 6 | 7-9 | 7-9 | 5-6 | 8-11 | 8-11 | 6-8 | 9-12 | 10-13 | 7-9 | 11-14 | 12-15 | 8-11 |
| 4 | Mountain King | 11 | 10 | 7 | 8-11 | 7-11 | 5-7 | 9-13 | 10-13 | 6-9 | 11-15 | 12-15 | 8-11 | 13-17 | 14-18 | 10-13 |
| 4 | Archmage | 13 | 11 | 8 | 9-12 | 9-12 | 6-9 | 11-14 | 11-14 | 7-10 | 13-16 | 13-17 | 9-13 | 14-19 | 15-20 | 11-14 |
| 8 | Dryad | 9 | 9 | 6 | 5-8 | 5-8 | 2-5 | 6-9 | 6-9 | 4-7 | 7-11 | 8-11 | 5-8 | 8-12 | 9-13 | 6-9 |
| 8 | Mountain King | 11 | 10 | 7 | 6-9 | 5-9 | 3-6 | 7-11 | 7-11 | 4-8 | 8-13 | 9-13 | 6-10 | 10-15 | 11-16 | 7-11 |
| 8 | Archmage | 13 | 11 | 8 | 6-10 | 6-10 | 4-7 | 8-12 | 8-13 | 5-9 | 9-14 | 10-15 | 7-11 | 11-17 | 12-18 | 8-13 |

v4.1:

| players | champion | Level 1 tower | Level 1 Nexus | Lane boss | L2 tower | L2 Nexus | L2 boss | L3 tower | L3 Nexus | L3 boss | L4 tower | L4 Nexus | L4 boss | L5 tower | L5 Nexus | L5 boss |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Dryad | 9 | 9 | 6 | 12 | 12 | 9 | 14 | 14 | 10 | 16 | 16 | 12 | 18 | 19 | 14 |
| 1 | Mountain King | 11 | 10 | 7 | 14 | 14 | 10 | 16 | 17 | 12 | 19 | 20 | 15 | 23 | 25 | 17 |
| 1 | Archmage | 13 | 11 | 8 | 16 | 15 | 12 | 19 | 19 | 14 | 22 | 24 | 16 | 27 | 32 | 19 |
| 2 | Dryad | 9 | 9 | 6 | 9-11 | 9-11 | 7-8 | 11-13 | 12-13 | 8-9 | 13-15 | 13-15 | 10-11 | 15-17 | 16-18 | 12-13 |
| 2 | Mountain King | 11 | 10 | 7 | 11-13 | 11-13 | 8-9 | 13-15 | 14-15 | 10-11 | 15-18 | 16-19 | 12-14 | 18-20 | 19-22 | 14-15 |
| 2 | Archmage | 13 | 11 | 8 | 13-15 | 13-14 | 9-11 | 15-17 | 15-18 | 11-13 | 18-20 | 19-21 | 13-15 | 20-24 | 22-27 | 15-18 |
| 4 | Dryad | 9 | 9 | 6 | 8-10 | 8-10 | 5-8 | 9-12 | 9-12 | 7-9 | 11-14 | 11-14 | 8-11 | 12-16 | 13-17 | 9-12 |
| 4 | Mountain King | 11 | 10 | 7 | 9-12 | 9-12 | 6-9 | 11-14 | 11-15 | 8-11 | 13-17 | 13-18 | 10-13 | 15-19 | 16-21 | 11-15 |
| 4 | Archmage | 13 | 11 | 8 | 11-14 | 10-14 | 7-10 | 13-16 | 13-17 | 9-12 | 14-19 | 15-20 | 11-14 | 17-22 | 18-25 | 13-17 |
| 8 | Dryad | 9 | 9 | 6 | 6-10 | 6-10 | 4-7 | 8-12 | 8-12 | 5-9 | 9-14 | 9-14 | 7-10 | 11-15 | 11-16 | 8-12 |
| 8 | Mountain King | 11 | 10 | 7 | 7-12 | 7-12 | 5-9 | 9-14 | 9-14 | 6-10 | 11-16 | 11-17 | 8-12 | 13-19 | 13-20 | 9-14 |
| 8 | Archmage | 13 | 11 | 8 | 9-13 | 8-13 | 6-10 | 10-16 | 11-16 | 7-12 | 12-19 | 13-19 | 9-14 | 14-21 | 15-24 | 11-16 |

**The final boss**: seconds to kill him if every champion keeps hitting (Dryad's mixed stats for everyone), and seconds one champion lives under him. A model. v4.1's times are shorter because growing no longer heals him.

v4.0:

| team gold of wave | minute | 1 players | 2 players | 4 players | 8 players | one life |
|---|---|---|---|---|---|---|
| 25 | 15 | 738 s | 333 s | 330 s | 241 s | 31 s |
| 30 | 20 | 735 s | 336 s | 333 s | 244 s | 38 s |
| 40 | 30 | 757 s | 351 s | 348 s | 257 s | 50 s |
| 40 | 50 | 1263 s | 578 s | 573 s | 421 s | 35 s |

v4.1:

| team gold of wave | minute | 1 players | 2 players | 4 players | 8 players | one life |
|---|---|---|---|---|---|---|
| 25 | 15 | 628 s | 308 s | 306 s | 228 s | 31 s |
| 30 | 20 | 638 s | 314 s | 311 s | 233 s | 38 s |
| 40 | 30 | 672 s | 331 s | 329 s | 246 s | 50 s |
| 40 | 50 | 1098 s | 540 s | 536 s | 401 s | 35 s |

Mixed in the model is not the probe's "starter": at wave 1 the model buys F5 A2 S2 for 937 g, the probe F4 A2 S2 and a potion for 924 g. They are different loadouts, so the two tables do not validate each other build for build.

Weakest and strongest, mixed build, in the model: **Pit Lord** loses the least and clears the fastest at every wave (17 % / 8 s at wave 1, 10 % / 8 s at wave 20). The one who loses the most is Dryad at wave 1 (36 %), Archmage at wave 5 (33 %) and **Far Seer** from wave 10 (40 % / 30 s at wave 20). That is a spread of 2 to 4 times. The champions still differ on purpose: nothing matches the monsters to what a player bought.

An Intelligence-only build gets +20 damage per buy and almost no HP or armor: a 358 to 404 % loss at wave 1 against 41 to 55 % for the other primary builds, so it is the worst primary build by far.

Only Dryad, Mountain King and Archmage were measured in real fights. Pit Lord, Far Seer, Lich and Tauren Chieftain are model only.

## What players should notice

- **1000 gold spent sensibly:** a real fight from the first wave. The starter's lowest point in wave 1 was 46 to 51 % of its HP gone.
- **Gold not reinvested:** the frozen starter first dies in wave 4, on all three champions. **Buying goes on:** the same start with every coin spent had 0 deaths in 7 minutes, up to wave 16 to 20.
- **One stat only is a risk:** Dryad clears wave 1 in half the time, with 252 of 550 HP left. Mountain King lives but takes longer and first dies in wave 3. Archmage dies in wave 1.
- **Careless buys:** dead in wave 1, 2 to 5 times.
- **Half the gold** costs 3 to 7 times the loss in the model.
- **Waves take longer:** 16 to 20 waves in 7 minutes, v4.0 had 20 to 24. The game clock runs further, and the final boss grows with the clock.
- **Holding a wave back for the Bank no longer pays indefinitely:** at most 120 counted seconds per wave. It still pays within that.
- **A leak is serious now:** the last 4 monsters of wave 3 destroyed the castle in under 2 minutes. The castle's own numbers are unchanged, so the castle shop matters more.

## Limits

- **Not measured:** a human player, fun or difficulty as felt. That is Jiří's call in a real game.
- **Not measured:** a whole campaign to victory, towers, Nexuses and bosses in a real fight. The bot does not push. Their base numbers are unchanged since v4.0, and the model's brackets are bounds, not proof.
- **Not measured:** stages 1 and 2 in a real fight. With every coin spent, the bot took 1 to 6 % of its HP per wave at stage 0 by waves 15 to 20. Whether the mid game is hard enough once players push is for a real game to show. `WAVE_HP_GROWTH` and `WAVE_DMG_GROWTH` in `gen/objects.py` are the two numbers to turn.
- **Not measured:** the castle under a real leak in a team game. Monster damage grew and the castle did not. If it proves too harsh, the castle's HP is one number.
- **Not measured:** several real players. Team sizes are the formula's values, tested on real units with a simulated count, and "picked and left" is a simulated state. A real leave has not been exercised.
- **Not measured in a fight:** that the Bank refuses a third payment. See above.
- **Solo lane, Scourge only** in real fights: a hidden run has one player, on lane 1. The other factions have the same numbers now, which the build's data shows, not a fight.
- Software rendering, one bot, seed 1: a small sample. Differences of a few seconds mean nothing.
- Premium items, castle upgrades and potions beyond the first are not in the bot's play. A player has more options than it does.

## Reproduce

```bash
tools/balance_matrix.py                                # the model, this tree
tools/balance_matrix.py --rev cffff32                  # the model, v4.0's numbers (needs ref/, the game's tables)
tools/balance_probe.py selfcheck                       # the log validation, no game
tools/balance_probe.py run LABEL --set fight           # real fights, hidden; also --set progress, --set stall
tools/balance_probe.py report LABEL
tools/test_env.py run                                  # mechanical regression
```

Evidence of the runs above is local, in `~/games/wc3-test-env/evidence/`. It is not in this public repo.
