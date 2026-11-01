# Balance

What was asked, the rule, and what was really measured. The rules and exact numbers live in [gameplay.md](gameplay.md), the code in
`WAVE_*` and `BOSS_*` of `gen/objects.py` and `Scale*`, `BossEquip`, `WavePayRatio`, `MinionBounty` of `gen/castle_logic.j`.

Jiří, 2026-11-01: bosses far too easy, far too many weak monsters, late play boring. Stronger regular monsters, much stronger bosses, fewer monsters at the cap. Bosses ultra fast, high damage, durable, not stunnable. Hero spells must still hurt them.

**Every lane has its own wave since v4.2.** All numbers are per wave of one lane.

## The rule (v4.3)

| What | Rule | Up to v4.2 |
|---|---|---|
| Wave size | Melee 5 + wave, at most 16. Ranged (wave + 1) / 2, at most 8. Every 10th wave adds wave / 10 wave champions, at most 6 | Melee 4 + 2 × wave, at most 40. Ranged = wave, at most 20. Same champions, not capped |
| Wave 1 | Melee 700 HP / 60 damage, ranged 420 / 120: unchanged, for the same first minutes | |
| Every wave, n = wave − 1 | HP × (1 + 0.092 n²), damage × (1 + 0.045 n²) | HP × (1 + 0.03 n²), damage × (1 + 0.018 n²) |
| Lane stage, factions, shared gates, rescaling, Bank | Unchanged, see below | |
| Gold and XP of a wave | A monster's kill gold and XP are multiplied by the old count / the new count (`WavePayRatio`, at most ×2.5), so a smaller wave pays what it paid with up to 60 monsters. A champion's kill does not get the ratio. A clear pays as before | Fewer monsters would have meant a lot less of both |
| Lane and gate bosses | HP × (1 + 0.02 n²), at most ×16. Attack × (1 + 0.008 n²), at most ×8. One attack per second, speed 522. Own spells of 10 levels: level 1 + wave / 5 + gate level, 1200 damage per level on one target. Their summons grow with the wave too. They shake off any stun at once and spell damage still lands. Numbers are set when they rise. | Fixed HP and damage whatever the wave, slower, stunnable, the same spell level for all |
| Final boss | Unchanged: his own clock growth | |

| Wave | Monsters | Melee HP / damage | Ranged HP / damage | Whole wave HP (v4.2) | Gold per kill | Clear gold | Lane boss HP with v4.4's gear / a hit |
|---|---|---|---|---|---|---|---|
| 1 | 7 | 700 / 60 | 420 / 120 | 4 620 (4 620) | 1 | 100 | |
| 3 | 10 | 900 / 70 | 520 / 140 | 8 240 (9 251) | 4 | 200 | |
| 5 | 13 | 1 700 / 100 | 1 020 / 205 | 20 060 (17 612) | 7 | 300 | 158 400 / 2 708 |
| 10 | 21 | 5 900 / 275 | 3 520 / 555 | 123 800 (79 233) | 17 | 550 | 314 400 / 3 957 |
| 20 | 26 | 23 900 / 1 030 | 14 320 / 2 065 | 640 560 (480 298) | 50 | 1 050 | 986 400 / 9 335 |
| 30 | 27 | 54 800 / 2 330 | 32 820 / 4 660 | 1 632 860 (1 120 021) | 75 | 1 550 | 1 920 000 / 18 555 |
| 60 | 30 | 224 800 / 9 455 | 134 920 / 18 915 | 8 723 760 (5 166 070) | 150 | 3 050 | 1 920 000 / 19 208 |

`tools/balance_matrix.py` prints this for any wave, with the gate bosses: a Level 5 boss at wave 44 has 23 million HP with its gear and hits for 64 800, with 8 players × 3.45 HP.

The target of a boss fight of 30 to 60 s with a legal loadout is a target. See the duels below.

## The rule (v4.4)

| What | Rule | Up to v4.3 |
|---|---|---|
| Tower down | A Tower Warden rises on the ruins, a boss of its own: 35 000 HP base, ~1800 a hit, its faction's spells, no adds; a gate's × its level | A Protector 920 behind the ruins: a champion with +450 HP |
| Bosses' gear | Real bound items. Warden / Nexus boss: Heart +50 / +100 % base HP, Gauntlets +50 / +100 % attack speed and 20 / 25 % chance of 2×, Warplate +25 / +40 armor and 20 / 25 % less spell damage | None |
| Boss spells | The native's own cooldown at every level (6 to 12 s) | 1 s from level 1 on: the engine's own use of a creep spell could fire two Frost Novas 1.8 s apart |
| Premium Armory | See gameplay: Fang 5 to 30 %, all eight on the same modest scale, 1000 gold a rank | Fang 30 to 70 % and the like |
| Circle prices | +5 % a buy, compound: step 99 costs 12 524 | +3 % |

`tools/balance_matrix.py` prints all bosses by wave with their gear.

## What was measured (v4.4)

**Four duels** (`balance-v44g`, all four pass the validation: the Fang's rank carried, 1000 gold a rank, the kit used). One champion, one boss, the lane's waves kept away. **A fixture, not a playthrough:** hero level, wave and gold are set, the purchases are real and legal: Fang rank 1 early, rank 5 late, the rest of the gold in All, All, Str, Agi at the shop's +5 % prices. Nothing heals or kills once it has begun. Ends at the first death or 120 s after first contact. One bot, seed 1, Scourge lane.

| Duel | Boss HP | Winner | Seconds | Hero's HP at the end | Boss's HP at the end | Damage: hero / from boss | Hero's casts / boss's casts |
|---|---|---|---|---|---|---|---|
| Mountain King vs Warden, wave 10, level 10, 5000 g | 137 500 | hero | 49 | 24 076 of 24 200 | 0 | 138 536 / 17 526 | 16 / 0 |
| Dryad vs Warden, wave 10, level 10, 5000 g | 137 500 | boss | 9 | dead | 131 606 | 5 910 / 9 373 | passive / 2 |
| Mountain King vs Nexus boss, wave 20, level 20, 20 000 g | 986 400 | boss | 110 | dead | 267 982 | 786 998 / 96 905 | 24 / 6 |
| Dryad vs Nexus boss, wave 20, level 20, 20 000 g | 986 400 | boss | 59 | dead | 850 400 | 174 871 / 62 065 | passive / 0 |

- **Far from uniform.** The Mountain King's Avatar makes him immune to spells: against the Warden he took 17 526 in 49 s and was never in danger, its spells never fired. Without such a shield the Dryad had 8475 HP and died in 9 s: one Frost Nova takes her from 8118 HP down, then the hits. At level 20 her own Spell Immunity keeps the boss's spells off too, and its attacks kill her in 59 s.
- **The Nexus boss beat both,** with its summons at its side (5284 of the Mountain King's damage taken came from them). A team was not played.
- **Channels:** the boss's own orders no longer break a running Blizzard, but the two here ended after 2.2 and 3.2 s (`finished=0`): the engine or the fight still interrupts them. No channel running to its end was seen in these fights.
- **Not tuned on this:** four fights say the numbers can hurt and that the spread between champions is large. They do not say the numbers are right.

**In the self-test, in real blows** (`20261101-233342-a-98e7`, on one fresh champion and plain monsters.

| Item, top rank | Measured |
|---|---|
| Vampire Fang 5 % and 30 % | Mountain King 5.0 % and 30.0 %, Archmage 5.0 % and 30.0 %, without it 0.0 %: healed at the hit over damage of the hit, 5 hits each |
| Fury Gloves +25 % | a hit every 1.48 s without, 1.22 s with |
| Executioner's Axe 20 %, 2x | 8 of 40 hits critical, none above 2x |
| Stormhammer 15 %, +25, 0.5 s | 4 bashes in 36 hits, the bash's own damage event 25, the shortest stun 0.50 s |
| Phantom Cloak 15 % | 86 hits of 108 attacks with it, 104 of 110 without |
| Winged Boots +50 | the engine reads 450 (400 without), walked 425 per second against 384 |
| Troll Heart +10 | 35.0 HP per second against 25.0 |
| Arcane Mask +50 % | 22.51 mana per second against 15.00 |
| Boss's Warplate | a hit 250 without, 85 with; a Storm Bolt 700 without, 525 with |
| Boss's Gauntlets | a blow every 1.00 s without, 0.50 s with; 10 of 49 blows critical, none above 2x |

Small samples: a chance here says it works and is about right, not its exact value. The Dryad with her whole kit and the Fang: her spears still hit 8 different foes in one volley and her poison lands; what the Fang heals in a volley was not measured. **A hero's own passive and the item both work, each with its own roll:** Mountain King's Bash alone 11 of 38 events at +1500, with the Stormhammer 15 of 44 and 2 small ones; Blademaster's Critical Strike alone 4 of 27 at 5x, with the Axe 9 at 2x or more and 3 of them at 5x; Dryad's Evasion with the Cloak 70 hits of 102 attacks.

## What was measured (v4.3)

**Four fights, nothing more** (`balance-v43`, all four pass the log validation): 180 s each, seed 1, one lane on the Scourge arm, production timings and prices, the starter loadout bought before wave 1 and frozen (All ×4, Str ×2, Agi ×2, potion: 924 of 1000 g). A simple bot plays with ordinary orders and casts what it has learned. Its Dryad learns Multiple Arrows first, because she has nothing to cast. 0 tower and Nexus hits in all four: monsters only.

| Champion | Learned, card order | Waves reached | Deaths | Wave 1: seconds, lowest HP | Own spells cast (`SPELL_EFFECT`, no items) | Damage: champion / his other units |
|---|---|---|---|---|---|---|
| Dryad | 3 2 0 0 1, Multiple Arrows 2 | 7 | 2, in waves 6 and 7 | 11 s, 2237 of 2550 | none to cast | 98 111 / 0 |
| Mountain King | 2 2 0 0 0 | 5 | 1, in wave 4 | 28 s, 1616 of 2800 | Storm Bolt 17, Thunder Clap 17 | 59 839 / 0 |
| Archmage | 2 2 0 0 0 | 5 | 2, in wave 5 | 21 s, 1334 of 2450 | Blizzard 9 (up to 12 s each), Water Elemental 4, Anti-magic Shield 4 | 39 838 / 5 295 (water elementals) |
| Beastmaster | 2 2 0 0 1 | 6 | 0 | 20 s, 2436 of 2725 | Summon Bear 4, Feral Spirit 8, Spirit Pig 5 | 14 145 / 62 797 (his summons, 25 summoned) |

- **Onboarding:** with 1000 g spent sensibly wave 1 is a real fight and nobody dies in it, nor in waves 2 and 3. Without buying anything more the first deaths come in waves 4 to 6, the Beastmaster has none in 180 s. These are the first minutes only.
- **The spells count:** the casters cast, the summons do most of the Beastmaster's damage. "Champion" damage is attack and spells together, so this does not split the Mountain King's or the Archmage's spells from their swings.
- **Channels:** the bot leaves a running Blizzard alone. It broke a spell only below 25 % HP, logged as `channel_cancelled`: the Archmage 6 times, the Mountain King twice.
- **The Dryad's spears** are measured apart, in the self-test with 12 enemies around her: 4 / 6 / 8 / up to 10 hit per attack at levels 1 to 4, and filmed. This fight only shows she has learned them and what she then deals in all.
- **Representative, not exhaustive:** a ranged champion, a melee, a caster and a summoner. Ultimates and level 20 abilities are covered by the self-test's cast table, not by these short fights.

## Three kinds of evidence, never mixed

1. **The tables above** (`tools/balance_matrix.py`): the game's own formulas, monsters and bosses. No fight. Champions are in no formula since v4.3: their strength is their real spells, only a game can show it.
2. **Real fights** (`tools/balance_probe.py`): the production game, hidden, played by a simple bot with ordinary orders, real purchases and its champion's real spells. A bot is not a player.
3. **The self-test** (`tools/test_env.py run`): mechanical regression. It gives itself gold and levels, pauses enemies and forces kills, so it says nothing about balance. It does check the rules.

## What players should notice

- **Fewer monsters, each one matters:** 13 at wave 5, 21 at wave 10, at most 30 a lane. Up to v4.2 it was 19, 35 and 60 plus champions.
- **A boss is an event:** it runs you down at speed 522, one hit a second, a stun buys nothing. A lane boss at wave 20 has 986 400 HP with its gear and hits for 9335.
- **Your wave is your own:** clear fast and you climb, and earn, faster, into a boss that rises as strong as your wave.
- **A leak is serious:** monster damage grew and the castle did not, and a leak walks about 720 further than before.

## Limits

- **Only four duels against bosses,** one lane, one bot, fixed level and gold, above. Whether a team kills a boss in the 30 to 60 s aimed at is open. `tools/balance_probe.py --set boss` mixes Warden, Nexus boss and new waves and has not run: unproven.
- **Not measured: waves past 7, and playing on with the gold spent.** No `progress` run on v4.3. That fewer monsters pay as much gold and XP as before is the formula (`WavePayRatio`, `UnitKillXp`) with a mechanical check, not a played economy. Stages 1 and 2 and the gates are mechanical checks only.
- **8 of 12 champions never fought a bot:** Tauren Chieftain, Pit Lord, Lich, Paladin, Blademaster, Crypt Lord, Demon Hunter, Priestess. The self-test casts their spells and checks each effect. How strong they are against each other is unknown and nothing was tuned between them.
- **Passive abilities** (auras, Bash, Critical, Evasion and others) are the native ones with the reference's numbers, not measured one by one. The reference map itself was not played side by side; the data is compared (`tools/xhs_port.py check`).
- **Not measured:** a human player, fun or difficulty as felt. That is Jiří's call in a real game.
- **Not measured:** several real players, also whether anything desyncs. A hidden run has one player. The team factor is the old formula.
- **Not measured:** the castle under a real leak in a team game. If it proves too harsh, the castle's HP is one number.
- Software rendering, one bot, seed 1: a small sample. Differences of a few seconds mean nothing. Premium items, castle upgrades and potions beyond the first are not in the bot's play.

## Reproduce

```bash
tools/balance_matrix.py                                # monsters and bosses by wave, no game
tools/balance_probe.py selfcheck                       # the log validation, no game
tools/balance_probe.py run v43 --set fight --only '^(dryad|mk|archmage|beastmaster)-starter-s1$' --slots b --workers 1
tools/balance_probe.py report v43
tools/balance_probe.py run LABEL --set duel --slots b --workers 1   # four duels; also --set progress, --set stall, --set smoke
tools/test_env.py run                                  # mechanical regression
```

Evidence of the runs above is local, in `~/games/wc3-test-env/evidence/`. It is not in this public repo.

## History: v4.0 to v4.2, the champions before X Hero Siege

**These numbers are for the old champions, old wave sizes and old growth.** They stay as the record of why the rule moved, and nothing in them holds for v4.3. Their model, `tools/balance_matrix.py --rev`, went with those champions: it is in the git history up to `cc8ae7c`.

### The rule (v4.1)

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
| Bank | At most 120 counted seconds of income per wave, renewed only by the next wave; always during the final boss. Since v4.2 per player: his own lane's next wave; once his lane is finished any wave |
| Shop | Health +600, Damage +20, Armor +8 (were +100, +5, +2), so that they compete with the stats that also give them |
| Unchanged | The base stats of towers, Nexuses and bosses (their HP now also grows with the team, see Shared gates), the final boss's clock growth, wave sizes, kill and wave gold, prices |

### Own waves (v4.2)

- **One player's lane plays as before** until the first Nexus falls: the same formula on the same number, and the same gold and tree per wave. The bot confirms it (seed 1, every coin spent, 420 s, one lane): Dryad 16 waves, Mountain King 20, Archmage 20, 0 deaths, as in v4.1, and the lowest HP in wave 1 is the same number (1239, 1466, 1316). Later waves spawned up to 20 s later or 5 s earlier, with no common direction across the three champions. Holding a wave back: again 2 payments in wave 3, and the last 4 monsters destroyed the castle at 214.6 s (v4.1: 231.7 s). This says nothing about two lanes side by side.
- **Between players the numbers now spread.** A fast player meets the stronger monsters and earns more; nobody waits. The growth is quadratic, so a lane that runs ahead also meets its own brake. No catch-up was added.
- **A gate** starts from the wave of the lane that opened it, so at that moment it is as strong as in v4.1 for a solo player. After that it climbs only when it is cleared.
- **More clears can pay in the same time:** a solo player with his lane and a gate open used to get one payment per joint clear and now gets one per lane. At wave 30 a clear pays 1550 gold while the kills of a Level 2 wave pay up to about 3600, so kill gold still leads.
- **Not measured:** all of this with several real players, and how far apart fast and slow players drift. A hidden run has one player and the bot does not push to a gate. The self-test shows the mechanics (below), not how they feel. Watch in a real game: a slow player's monsters at the castle while the fast ones cannot pause to help.

### Three kinds of evidence, never mixed

1. **The model** (`tools/balance_matrix.py [--rev REV]`): formulas over the game's real tables. No pathing, healing or potions; a fixed number of attackers and targets. It shows trends and compares champions. Its loadouts and budgets are not the bot's, so it does not predict a real fight.
2. **Real fights** (`tools/balance_probe.py`): the production game, hidden, played by a simple bot with ordinary orders and real purchases. A bot is not a player.
3. **The self-test** (`tools/test_env.py run`): mechanical regression. It gives itself gold and levels, pauses enemies and forces kills, so it says nothing about balance. It does check the rules: a scale applied twice changes nothing, a wounded unit that grows does not heal, the shared HP formula for 1, 2, 4 and 8 players, a real personal spawn with team 1 and a real gate spawn with a simulated team of 4, a player who picked and left (a simulated state), the real first wave after a restart, and the Bank's budget, kill rule and renewal. Since v4.2 also the lanes: real monsters of two lanes with their own waves and HP, each lane's next wave coming only when that lane is clear, with the other held back by one living monster; who gets paid; a gate starting from its opener's wave and climbing by itself; a finished lane staying quiet; everything starting over on *Play again*. The second lane is a simulated second player and the kills are forced. **113 PASS, 0 FAIL** (`20261101-182958-a-4d9d`, TEST map `26a6386d…`). v4.1 had 97 of these on map `3532ceed…`.

### Real fights

Seed 1, a solo lane on the Scourge arm, ordinary orders, production timings, normal 1000 gold, legal purchases. The same bot played v4.0 and v4.1, and during a measured fight nothing changes HP, gold, level or time. **Every run had 0 tower and Nexus hits**, so these are monster fights only. A failed fight stays in the data.

Three loadouts, bought before wave 1 and frozen for the 180 s of the run: **starter** = All ×4, Str ×2, Agi ×2, potion (924 g); **primary** = primary stat ×8, potion (989 g); **careless** = Mana ×4, Damage ×4 (836 g).

#### Frozen loadouts: 180 s

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

#### Frozen loadouts: wave 1

First hit and clear in seconds after the spawn. **Min HP** = the lowest HP in the wave, **taken** = all damage received, which can be more than the HP lost. Dealt = HP removed from monsters by the champion. \* = the clear was not confirmed: the time is where the next wave began.

| Champion | Loadout | HP | v4.0 first hit / clear / min HP / taken / dealt | v4.1 first hit / clear / min HP / taken / dealt |
|---|---|---|---|---|
| Dryad | starter | 2550 | 4.8 / 11 / 2479 / 101 / 1313 | 4.8 / 26 / 1239 / 1419 / 4596 |
| Dryad | primary | 550 | 6.1 / 8 / 542 / 7 / 1316 | 4.8 / 13 / 252 / 307 / 4607 |
| Dryad | careless | 550 | 4.8 / 42\* / 0 / 1006 / 1307, 1 death | 4.8 / 92 / 0 / 2945 / 4597, 5 deaths |
| Mountain King | starter | 2700 | 4.4 / 12 / 2618 / 116 / 1366 | 4.4 / 22 / 1466 / 1326 / 4747 |
| Mountain King | primary | 4700 | 4.4 / 14 / 4410 / 369 / 1391 | 4.4 / 28\* / 1825 / 4007 / 4688 |
| Mountain King | careless | 700 | 4.4 / 32 / 0 / 1001 / 1345, 1 death | 4.4 / 89 / 0 / 4323 / 4657, 5 deaths |
| Archmage | starter | 2450 | 4.8 / 11 / 2370 / 102 / 1323 | 4.8 / 22 / 1316 / 1256 / 4652 |
| Archmage | primary | 450 | 4.8 / 11 / 277 / 177 / 1349 | 4.8 / 23\* / 0 / 961 / 4619, 1 death |
| Archmage | careless | 450 | 4.8 / 24\* / 0 / 480 / 1344, 1 death | 4.8 / 40 / 0 / 1214 / 4641, 2 deaths |

#### Frozen loadouts: waves 2, 3, 5

Each cell: seconds in the wave, min HP / the loadout's HP before wave 1. That second number stays the same in every wave. Every level-up raises max HP and refills HP, so min HP can pass it and can rise from wave to wave without a purchase.

| Champion | Loadout | Wave | v4.0 | v4.1 |
|---|---|---|---|---|
| Dryad | starter | 2 | 12 s, 2494 / 2550 | 33 s, 1010 / 2550 |
| Dryad | starter | 3 | 14 s, 2480 / 2550 | 33 s, 212 / 2550 |
| Dryad | starter | 5 | 12 s, 2554 / 2550 | 8 s (open at the end), 656 / 2550 |
| Dryad | primary | 2 | 10 s, 529 / 550 | 17 s, 188 / 550 |
| Dryad | primary | 3 | 10 s, 530 / 550 | 18 s, 34 / 550 |
| Dryad | primary | 5 | 9 s, 641 / 550 | 36 s, 0 / 550, 1 death |
| Dryad | careless | 2 | 61 s, 0 / 550, 2 deaths | 57 s (open at the end), 0 / 550, 3 deaths |
| Dryad | careless | 3 | 47 s (open at the end), 0 / 550, 2 deaths | - |
| Mountain King | starter | 2 | 12 s, 2674 / 2700 | 22 s, 1383 / 2700 |
| Mountain King | starter | 3 | 13 s, 2659 / 2700 | 22 s, 1096 / 2700 |
| Mountain King | starter | 5 | 12 s, 2849 / 2700 | 39 s, 0 / 2700, 1 death |
| Mountain King | primary | 2 | 14 s, 4511 / 4700 | 27 s, 522 / 4700 |
| Mountain King | primary | 3 | 16 s, 4481 / 4700 | 42 s, 0 / 4700, 1 death |
| Mountain King | primary | 5 | 8 s, 4519 / 4700 | 11 s (open at the end), 1191 / 4700 |
| Mountain King | careless | 2 | 35 s, 0 / 700, 1 death | 60 s (open at the end), 0 / 700, 3 deaths |
| Mountain King | careless | 3 | 39 s, 0 / 700, 1 death | - |
| Archmage | starter | 2 | 11 s, 2386 / 2450 | 22 s, 962 / 2450 |
| Archmage | starter | 3 | 12 s, 2385 / 2450 | 20 s, 1192 / 2450 |
| Archmage | starter | 5 | 12 s, 2515 / 2450 | 43 s, 0 / 2450, 1 death |
| Archmage | primary | 2 | 11 s, 329 / 450 | 26 s, 0 / 450, 1 death |
| Archmage | primary | 3 | 12 s, 285 / 450 | 53 s, 0 / 450, 3 deaths |
| Archmage | primary | 5 | 10 s, 465 / 450 | 1 s (open at the end), 160 / 450 |
| Archmage | careless | 2 | 29 s, 0 / 450, 1 death | 57 s, 0 / 450, 3 deaths |
| Archmage | careless | 3 | 27 s, 0 / 450, 1 death | 45 s, 0 / 450, 2 deaths |
| Archmage | careless | 5 | 34 s, 0 / 450, 1 death | - |

#### Playing on: 420 s

Starter, then every coin into All, All, Str, Agi and every tree into the Bank. Stage 0 only: the bot does not push. Cell: seconds in the wave, HP taken, min HP, level, gold spent. `-` = not reached.

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

#### Holding a wave back for the Bank

Dryad, starter, no further purchases, income 200. From wave 3 she walks away from the last monsters and stays away.

| | v4.0 | v4.1 |
|---|---|---|
| Wave 3 | spawned at 54 s, still open at the end, 420 s | spawned at 90 s, still open at the defeat, 231.7 s |
| Monsters left, no new kill | 3, from 90 s to 420 s | 4, from 114.5 s to 231.7 s |
| Payments of +200 in wave 3 | 7: one at 60 s, then 6 further after 90 s, up to 420 s | 2: at 120 s and 180 s, then the game was over |
| Castle | 8000 → 4960 at 390 s, about 10 HP per second | 8000 → 0, about 90 HP per second, **destroyed at 231.7 s** |

This real run shows two things: v4.0 paid for as long as a wave stood, and in v4.1 the last monsters of a wave are dangerous to the castle. It does **not** show that a third payment is denied: the castle fell 8 s before the payment at 240 s. The cap of 120 counted seconds and the kill rule are shown by the self-test's mechanical checks of `BankTick`. The renewal by a player's next wave has a state check since v4.2 (`BankRenew`). None of this comes from this fight.

#### Evidence

Under `~/games/wc3-test-env/evidence/`: `balance-v40-safe3-dryad` and `balance-v40-safe3` (v4.0), `balance-cand1` and `balance-cand1p` (v4.1), `balance-v40-stall1` and `balance-cand1s3` (the Bank), `balance-v42-p` and `balance-v42-s` (v4.2, one lane). All passed the log validation. Earlier batches (`balance-calib-v40-bot-limiter`, `balance-safe3-calib`, `balance-v40-safe2`, `balance-cand1s`, `balance-cand1s2`) are calibration of the bot or stalls that did not hold, and are not in the tables. Jiří's own game started during `archmage-progress` of `balance-cand1p` and both Bank runs: they are separate games, but for those three runs the check of zero change in personal files could not apply.
