# Changelog

## v4.3 — 2026-11-01: twelve champions of X Hero Siege, wider lanes, fewer and far stronger monsters, ultra fast bosses

- Jiří: "implement the champions of X Hero Siege 3.28, because the Dryad there throws several spears at once" → then: the twelve best, one tavern, the Dryad copied completely, the others with their real abilities. "Lanes too narrow at wave 23, melee behind, ranged in front." "Bosses far too easy, far too many weak monsters, late play boring." "Bosses ultra fast, high damage, durable, not stunnable." "Castle Regeneration should show what was bought." → [docs/gameplay.md](docs/gameplay.md) § Champions, § The map, [docs/balance.md](docs/balance.md)
- **12 champions from the reference, in the one tavern:** Dryad, Mountain King, Tauren Chieftain, Pit Lord, Archmage, Lich, Paladin, Blademaster, Beastmaster, Crypt Lord, Demon Hunter, Priestess of the Moon. `tools/xhs_port.py` generates `gen/xhs_data.py` from the local reference map, read-only, numbers and art paths only; the reference stays out of this repo. Their abilities are the native ones with the reference's numbers, a few triggers where it has triggers (`HeroGrants`, `OnHeroGlue*`), our own short text. The old champion layer, spear dummies included, is gone.
- **The Dryad's spears are the real thing now:** the native Barrage. Measured: 4 / 6 / 8 / up to 10 enemies hit per attack at levels 1 to 4, her own hit included, seen as simultaneous spears in a film. See gameplay and gotchas for the rules this ability really has: it goes with her attack and does the damage of her weapon, not the fields' 250 to 2000.
- **Integration differences, on purpose:** Attributes off the learn card, because a hero has at most 5 learnable abilities: from level 21 every level-up adds +30 to all stats. Max hero level 1000 stays. Our gameplay constants stay except the speed cap. Natives our bosses also use got their own ids. The Far Seer is not in the reference and is gone. Stat purchases stay.
- **Map:** 128 × 128 tiles, every lane and gate corridor 1280 wide (was 640), plaza 4608. **At the spawn melee stand in front towards the castle, ranged behind** (`SpawnRanks`), 128 apart, because the engine swaps units at 96. That is the order they start in, not a battle formation: once they fight or fly, the game moves them as it likes. A leak walks about 720 further to the castle. `tools/layout_audit.py` checks all of it on paper and draws it.
- **Waves:** fewer, far stronger: at most 16 melee + 8 ranged + 6 champions a lane (was 40 + 20). HP × (1 + 0.092 n²), damage × (1 + 0.045 n²). A wave pays the gold and XP it paid with up to 60 monsters.
- **Bosses:** HP and attack grow with the lane's wave, one attack per second, speed 522, spell level with the wave and gate, summons scaled, a schedule that really fires (due flags instead of unreachable modulo steps). Every boss shakes off a normal stun at once and its spell damage still lands. Impale is the measured exception: its damage lands when the boss comes down, so its stun is cleared after about 1.3 s, not at once. No magic immunity.
- **Castle Regeneration:** the item's name shows what was bought, "+50 HP/s" after 5, the next +10 in its tooltip. Same slot, key and price.
- **Play again was broken, in every version so far:** the game's hero limits count every native hero ever hired, and removing, giving away or killing him does not lower the count. From the round after a native hero on, the player's pick was refused and he got a random champion. The tests never saw it: they bought the custom Dryad first. The map no longer sets those limits; `OnUnitSold` enforces one champion per player per round.
- **Doom:** the native row has one level, so in our 1.27b runs the copied level 2 refused every monster of the creep race, also ours (the whole reference map was not run to see this there). The map carries the game's whole `Units\AbilityData.slk` with that one cell changed, generated at build and checked for exactly one difference (A/B in the gotchas). It costs 111 KiB: **the map is now 474 KiB** (v4.2: 319), over the guideline of about 200 as v4.2 already was. The native fix needs the whole table.
- **The bot:** it casts its champion's kit, keeps a running channel, claps only inside the radius, and its logs and validation carry ranks, spell ids, channel lengths, summons and other units' damage.
- **Verified, self-test:** 382 PASS, 0 FAIL in about 10 min (`20261101-215309-a-4325`, TEST map `ec17ae16…`). New: 13 real selections through restart, tavern and `AssignHero`, all 12 champions and the first one again; a second champion sold during a selection, and one sold outside it with and without a champion: none stays. Doom on the real melee monster at both levels, the level 5 and level 6 limits, 2 Doom Guards. Ranks and march on all 12 lanes in their real stages, Level 5 behind a fallen Level 4, plus a labelled impossible stress pass with all 12 at stage 0: one Abomination that stood still at 7 s (order attack) walked on by 14 s, nobody stood in the real states. The run before had one unit standing on lane 10 at 7 s, before this per-unit log existed: not explained, not seen again. Since that run only the map description changed, by audit of every file in the map (`war3map.j` one line, `war3map.w3i`), so it was not rerun. Also in the map's evidence: films of the tavern card, the Dryad's volley, the formation and the fullest card. Play again, six rounds with repeated champions: `20261101-213203-a-750d`. The hidden count: `20261101-212039-a-9395`.
- **Verified, on paper:** `tools/xhs_port.py check`, `tools/layout_audit.py` 160 checks, 0 failures, picture in `dist/layout-preview.png`.
- **Verified, bot, four fights of 180 s only:** Dryad, Mountain King, Archmage, Beastmaster, starter frozen, seed 1 (`balance-v43`): 7, 5, 5 and 6 waves reached, 2, 1, 2 and 0 deaths, none before wave 4, 0 tower hits, their spells cast, table in docs/balance.md. They ran on the release's game code plus the bot.
- **NOT verified:** a boss in a real fight (the 30 to 60 s target is only a target, `--set boss` has not run), waves past 7 and a played economy, stages 1 and 2 and the gates in a fight, 8 of 12 champions in any fight, passive abilities one by one, the reference played side by side, several real players and desyncs, a human player, difficulty or fun as felt, how it looks on a GPU. The `war3` launcher's fresh start also stays untested. Limits in docs/balance.md.

## v4.2 — 2026-11-01: every lane has its own wave

- **Uploaded as catalogue map #79** (HTTP 201, download SHA-256 `1bf9d59d…` matches dist and the installed map; 30 versions in the family).

- Jiří: "every lane will have its own wave levels! each player will have its own wave level based on how fast he cleans it!" → [docs/gameplay.md](docs/gameplay.md) § Every lane has its own wave
- **Each lane counts by itself** (`gLaneWave`): its next wave comes when THAT lane is clear, its 10th wave gives that lane its break, and its number sets size, HP, damage and kill gold. A slow player holds back nobody but himself. It used to be one counter, and everyone waited for the last monster on the map.
- **A clear pays the lane's player only**, `50 + 50 × his wave` gold + 1 tree. It used to pay everyone.
- **Scoreboard:** a Wave column per player (`done` when the lane's boss is dead), a row per opened gate. The title no longer shows a wave. News and the countdown go to the lane's player only.
- **Bank:** per player since it hangs on the wave: his own next wave renews it.
- **Decided without asking Jiří, his to overrule:** a gate starts from the wave of the lane that opened it and comes 30 s after opening. A gate's clear pays everyone. The lane of a player who left goes on and pays the others. A finished lane's Bank is renewed by any wave. No catch-up. Castle Shockwave on a boss uses the highest wave. Level 2 now only comes with your own first clear, not when others clear theirs.
- `build.py` refuses unknown options: `--help` ran a real build and put the untested map into the game folder, replacing v4.1. Restored at once by checksum; the game was running another map and had neither file open.
- **Verified, self-test:** 113 PASS, 0 FAIL (`20261101-182958-a-4d9d`, TEST map `26a6386d…`, rebuilt byte-identical before release). 16 new checks with real monsters and the real clear check, forced kills: lanes with their own waves and HP in both directions, who gets paid, the gates, a finished lane, *Play again*. The second lane is a simulated second player. A screenshot shows the Wave column and the Level 2 row.
- **Verified, bot on one lane (`balance-v42-p`, `balance-v42-s`):** the same as v4.1: Dryad 16 waves, Mountain King 20, Archmage 20, 0 deaths, the same lowest HP in wave 1. Holding a wave back still pays 2 times. So the v4.1 fight tables stand for one lane before the first Nexus.
- **NOT verified:** a real game with several players, including that nothing desyncs (only display calls are per player: countdown, sound, pings, like the revive countdown). How far fast and slow players drift apart. A gate in a real fight. A real leave. Fun and difficulty as felt.
- **To watch in a real game:** a lane no longer rests while another is cleared, so helping a friend costs time on your own lane. A slow player's monsters at the castle can end the game for everyone while the fast ones cannot pause.

## v4.1 — 2026-11-01: stronger monsters, smart scaling

- **Uploaded as catalogue map #78** (HTTP 201, download SHA-256 `354e5f1f…` matches; 29 versions in the family).

- Jiří asked for stronger monsters and smart scaling: a level 1 champion should struggle, winning should not be trivial, and players should think about upgrades and cooperate. → [docs/balance.md](docs/balance.md)
- **Wave monsters:** melee 700 HP / 60 damage, ranged 420 / 120 (were 200 / 30, 120 / 60). With n = wave − 1: HP × (1 + 0.03 n²), damage × (1 + 0.018 n²). They used to grow only in number. Stage: HP ×1.5 / ×2, damage ×1.25 / ×1.5 (were ×2 / ×3 for both).
- **Factions now share one set of combat values**: only the model and the movement type differ.
- **Shared gates:** HP × (1 + 0.35 (team − 1)) for gate monsters, Protectors, towers, Nexuses and bosses, mainly HP, never damage. Personal lanes don't scale with players: each player already adds a lane. Team = the players at the start of the round. Leaving lowers nothing, because the others control that champion.
- **A rescale never heals**, the final boss included: he used to keep his percentage, which gave him free HP every minute. His clock growth is unchanged.
- **Bank:** at most 120 counted seconds of income per wave, renewed only by the next wave, always during the final boss. A wave held back used to pay for as long as it stood.
- **Shop:** Health +600, Damage +20, Armor +8 (were +100, +5, +2), so they compete with the stats that also give them. **Castle Shockwave:** 25 % of a wave monster's max HP, because a fixed amount meant nothing against the new HP.
- **Tools:** `tools/balance_matrix.py` (the model), `tools/balance_probe.py` and `gen/probe.j` (the production game played hidden by a bot with ordinary orders; only in `build.py --probe`).
- **Verified, real fights** (seed 1, solo lane, same bot, 0 tower and Nexus hits): Dryad starter wave 1 from 11 s and 2479 of 2550 HP to 26 s and 1239. Frozen starter first dies in wave 4 on Dryad, Mountain King and Archmage; v4.0 had no death in 180 s. Archmage primary dies in wave 1. Careless dies in wave 1. With every coin spent: Dryad 16, Mountain King 20, Archmage 20 waves in 7 minutes, 0 deaths (v4.0: 20, 21, 24).
- **Verified, Bank:** v4.0 paid 7 times during wave 3, including 6 further payments after 90 s without another kill. In v4.1 wave 3 stood 141.7 s with 2 payments, then the last 4 monsters destroyed the castle at 231.7 s: a real defeat, 8 s before a third payment could fall due.
- **Verified, self-test:** 97 PASS, 0 FAIL on map `3532ceed…` (`wip-selftest-3`). A source audit found only comments, the version and two Bank tooltips changed after it, so it was not rerun. Test-only change: the castle is invulnerable from clock 5, because stronger monsters kill it during the checks.
- **NOT verified:** a human player, difficulty or fun as felt. A whole campaign to victory, and towers, Nexuses and bosses in a real fight (the bot does not push). Stages 1 and 2 in a real fight. Real team games: the formula is checked for 1, 2, 4 and 8 players, real units only with team 1 and a simulated team of 4, and a real leave was never exercised. That the Bank refuses a third payment in a real fight: the self-test's mechanical checks show the cap, and only the code shows its renewal by the next wave. Pit Lord, Far Seer, Lich and Tauren Chieftain are model only.
- **To watch in a real game:** with every coin spent, the bot took 1 to 6 % of its HP per wave at stage 0 by waves 15 to 20, and a leak costs the castle about 9 times as many HP per second. `WAVE_HP_GROWTH`, `WAVE_DMG_GROWTH` and the castle's HP are the numbers to turn.

## Docs — 2026-11-01: the website around this map

- Jiří: "přidej k tomu ještě i kontext o celým tom našem toolu v TechTools". [docs/techtools-warcraft-tool.md](docs/techtools-warcraft-tool.md): the web tool and its
  repo, LAN and VPN, accounts, catalogue, voice, messages, what lives where, dated 2026-11-01 with open points. No server code and no private data.
- Verified against `techtools-4` at `9b1d3cc`, `1497fd1` and `fcd2838`, and live API answers. The live message checks are the release coordinators' results, attributed as such.

## Test tooling — 2026-11-01: a hidden test environment (no map change, no new version)

- Jiří: test the map in the background while he plays, without "Warcraft III is already running".
- **`tools/test_env.py` replaces `tools/run_test.sh`.** One command, `tools/test_env.py run`: own Wine prefix and wineserver, own copy of the game
  (allow-list, real files), own Xvfb with a private cookie, software Vulkan, audio driver off, results, temp and crashes inside the slot.
  Exit 0 only on a fresh `SELFTEST DONE`, no `FAIL`, no new or changed crash file. Every run keeps its evidence under
  `~/games/wc3-test-env/evidence/`. Cleanup targets only the slot, by environment marker, PID and start time; a watchdog covers a killed runner. → [docs/test-env.md](docs/test-env.md)
- Why the old runner went: it opened a window on his desktop, refused to run while he played, and killed by a process-name pattern.
- **Verified** (hashes and evidence in docs/test-env.md): 60 PASS, 0 FAIL in about 170 s under Xvfb and lavapipe, screenshots show the game; error paths 37 of 37; two hidden
  clients 30 of 30, twice; zero change in the real game tree and `~/.wine` registry, 15 crash folders before and after.
- **NOT verified:** beside Jiří's real client. His game never ran during these tests, so the concurrency is simulated, and how his game feels beside a test is unknown.
  Software rendering checks the map's logic, not how it looks on a GPU.
- Rollback: `git show 9cba731:tools/run_test.sh > tools/run_test.sh`. A comment in `gen/castle_logic.j` still names the old runner: this change touches no map source.

## v4.0 — 2026-11-01: the final boss

- **Uploaded as catalogue map #77** (HTTP 201, download SHA-256 `04c52fdc…` matches; 28 versions in the family).

- Jiří: "the final boss will be ultra strong: stats based on the minute, immune to stuns, his own stun skills".
- **Kharazul the World Ender** (`nbf0`) rises when every lane boss and all 4 gate levels are done (`CheckVictory` →
  `StartFinalBoss`): waves stop, the castle is shielded, a 30 s warning, then he stands south of the castle, leashed to
  the plaza. **Victory is now his death** (`OnFinalBossDead`), no longer the last gate boss.
- **Stats by the game minute m**, also during the fight (`FinalApplyStats`): max HP (5 000 000 + 250 000 m) × 1 / 2 / 3 by
  player count, damage 20 000 + 1000 m, armor 30 + m / 2, spell tier +1 every 5 minutes; his HP % stays when he grows.
  1.27 can't set these directly: binary "bit" abilities with distinct ids stack (`FinalBits`).
- **Stuns don't hold him:** `FinalImmuneTick` (0.05 s) removes `BPSE` / `BSTN` and shows "Stun immune!".
- **His skills** (`FinalBossTick`): Storm Bolt, War Stomp, Shockwave, Inferno on a fixed schedule, passive Bash; he picks
  the nearest champion first and ignores invulnerable units (`FinalFindTarget`). The scoreboard title shows his HP.
- **Doc correction:** lane bosses always spawn the middle tier (60 000 HP, ~2400 per hit) at any player count; the
  "by player count" numbers in the docs and in the v3.9 entry below were wrong.
- `tools/run_test.sh`: the game runs in a small Wine virtual desktop (a click or focus loss on the normal window seems to
  pause the game: a whole run froze at 0:11) and closes itself on the new `SELFTEST DONE` line (Jiří's rule: close your own
  test game).
- **Verified in-game (Wine, full self-test): 60 PASS, 0 FAIL, no crash, 162 s.** This is also the first in-game run of
  v3.5–v3.9: 7 champions with R Lv 3 (2–3 storms in 10–16 hits each), first Spear Storm throws exactly 14 spears, spear
  dummies and pending damage cleaned up, stress 215 of 240 wave-20 monsters in 19 s. Final boss: rises after the warning;
  max HP 5 200 000 at minute 1 (formula 5 250 000, rounded down to the 100 000 step); castle takes no damage; a real Storm
  Bolt's stun removed at once; +5 minutes: HP 6 500 000, damage +6000, armor +3, tier 0 → 1, still 50 % HP; Storm Bolt 2,
  War Stomp 2, Shockwave 2, Inferno 1 casts; no more waves; his death = victory; Play again clears the final phase.
- **Not verified:** seeing the spears fly (the test camera wasn't on her); his spells against real champions (test
  targets were paused Taurens); the 2× / 3× HP with more players (the test has one player); the balance of all v3.9 / v4.0
  numbers in a real fight.

## v3.9 — 2026-11-01: much stronger towers, Nexuses and bosses

- **Uploaded as catalogue map #76** (HTTP 201, download SHA-256 `19edd60e…` matches; 27 versions in the family).

- Jiří: "towers damage 10x and health 5x, and Nexuses and inhibitors; the better the building, the more damage;
  bosses health 10x and damage 50x".
- **Towers:** HP ×5, damage ×10 — Level 1 20 000 HP / ~25 000 per hit, gates 32 500 → 105 000 HP / ~35 000 → ~80 000.
- **Nexuses:** HP ×5 (15 000; gates 40 000 → 200 000). Their damage was *below* their own tower's (900 + 4d40 vs ~2500),
  so "the better the building, the more damage" sets each Nexus ~10 % above its tower: ~27 500, gates ~38 500 → ~88 000
  (effectively ×25–28). `building_ladder` asserts at build time that every next building hits harder and that every
  next level has more HP.
- **Bosses:** HP ×10 (lane 35 000 / 60 000 / 90 000 by player count; gates 180 000 → 720 000), damage ×50 (lane
  ~1800 / ~2400 / ~3000; gates ~3350 → ~8100). Protectors and wave units unchanged.
- **Verified:** pjass + build checks incl. the new ladder assertion. ⚠️ Not run in-game (the self-test kills buildings
  and bosses with `KillUnit`, so it doesn't measure the new numbers either).

## v3.8 — 2026-11-01: the Hall of Champions moves to a small room in the top-right corner

- **Uploaded as catalogue map #75** (HTTP 201, download SHA-256 `1183ef42…` matches; 26 versions in the family).

- Jiří: "move the Hall of Champions to the top right corner and make it as small as possible, so monsters from the
  nearby lanes' Nexus don't spawn there like now".
- Cause (most likely): the old 1536 × 1536 hall in the NW lay 512 from the Frozen Gate's tower spawn; `CreateUnit`
  places a unit on the nearest free pathable spot regardless of walls, so a big wave spilled into the hall.
- `gen/layout.py`: `HALL_CENTRE` (−3200, 3200) → **(5632, 5504)** (empty NE corner, inside the camera bounds),
  `HALL_HALF` 768 → **384** (768 × 768 room); tavern at +160, the invisible buyers at −128 (`HALL_SOUL_DY`). Checked:
  no walkable floor within 768 of the hall, nearest spawn / Nexus 2320 away; top-down preview rendered.
- The tavern sells within **600** (was 1600): enough for the buyers in the hall, nobody outside can buy a hero.
  "Select a Champion" text sits just above the smaller room.
- **Verified:** pjass + build checks, preview render. ⚠️ Not run in-game yet (Jiří was playing).

## v3.7 — 2026-11-01: a clean Dryad multishot (review fixes)

- **Uploaded as catalogue map #74** (HTTP 201, download SHA-256 `97628cf3…` matches; 25 versions in the family).

- An adversarial code review of v3.5/v3.6 (3 lenses, every finding re-checked by a skeptic: 16 confirmed, 1 rejected)
  found why spears still looked messy; all fixed here:
  - **Spears re-aimed at far towers:** a dummy whose enemy died before its damage point went idle and auto-acquired
    anything within 2000. Now every dummy remembers its enemy (`gSpearTgt[slot]`, slot = user data), is stopped in
    `OnAttacked` if it attacks anything else, deals damage only to its own enemy, and has range 800 / damage point 0.
  - **Spears launched late** (fixed 0.3 s while her attack speed shortens her wind-up) and **even when her attack was
    cancelled:** the extra spears now leave at her real release moment — `DryadReleaseDelay` (0.3 s ÷ attack-speed
    factor: 2 % per agility, Swift Throw, Fury Gloves, capped at +400 %) on a per-player timer (`gVolleyTimer`,
    `VolleyRelease`); a new point / immediate order cancels it (`OnHeroOrder`), a restarted attack restarts it. The
    Spear Storm counter counts real throws. Dummies shoot from her launch point (0, 0, 100).
  - **Spears at corpses:** damage in flight is now "pending" per target (`gSpearHT`, `SpearPending` / `SpearResolve`);
    a throw skips enemies the spears in flight will kill.
  - **More levels threw fewer spares** (all-or-nothing rule): now as many spares as the target survives. **Spares
    overlapped** on one path: each starts beside her (25 / 50 / 75 / 100, alternating sides).
  - **Death scream and blood** from every dummy (Archer model events): dummies are never killed — `SpearSweep` (0.1 s)
    removes spent ones and any older than 4 s.
  - `-wave 0` was impossible (`DevArg` reads 0 as "no number"): new `PaceArg`. Restart and a new hero reset the last
    hit and the skill counters (`gLastHit`, `gVolleyCount`, `gStormCount`, `gHitCount`, `gAtkTarget`), and restart
    resolves and removes spears in flight. Stale docs fixed ("spells maxed at level 10", old wave/Bank numbers);
    three new gotchas in `docs/wc3-127-gotchas.md`.
- Self-test: the Dryad shoots into 16 paused Taurens; the first Spear Storm must throw exactly 14 spears; 5 s after
  her death no spear dummy and no pending damage may remain.
- **Verified:** pjass + build checks (normal + TEST). ⚠️ **Not run in-game yet** — Jiří was playing.

## v3.6 — 2026-11-01: every champion has 4 spells — Q, W, E and an R ultimate

- **Uploaded as catalogue map #73** (HTTP 201, download SHA-256 `196cb49f…` matches; 24 versions in the family).

- Jiří: "all champions should have 4 spells! Q, W, E, R!" (the Dryad had only Q W E).
- **R = ultimate, 3 levels at hero level 6 / 11 / 16** (`R_LEVELS`, `R_REQ_LEVEL`, `R_LEVEL_SKIP`, `skill_levels`), a
  passive `AEev` level holder like Q/W/E, learn key R, command-card slot (3, 2). The build asserts that every
  champion's skills are exactly Q, W, E, R.
- **Storm** (new kind 6) for the 6 AoE champions — Avatar (MK), Stampede (TC), Inferno (PL), Flame Strike (AM), Frost
  Wyrm (Lich), Thunderstorm (FS): every 5th primary hit deals 100 / 200 / 300 % of the hit to the target and every
  enemy within 650 (`STORM_*`), a big effect on the target and a small one on every victim (`SKILL_FX2`,
  `AoeDamageFx`). **Spear Storm** (kind 7) for the Dryad: every 4th throw +3 / 6 / 9 spears through `SpearVolley`
  (other enemies in her range; spares at the target only if it survives them).
- Hero tooltips list the skills from the data (`skills_line`); `check_fx` now fails the build on a missing effect model.
- Self-test: 4 skills per champion (`gSkPer`); test heroes level 16 with R 3; their targets are paused Taurens so the
  5th-hit storm surely fires; new checks: every AoE champion's storm fired, the Dryad's Spear Storm volleys.
- **Verified:** pjass + build checks (normal + TEST), generated R data (3 levels, 6/11/16, key R, slot (3, 2)).
  ⚠️ **Not run in-game yet** — Jiří was playing.

## v3.5 — 2026-11-01: Dryad multishot fixed, waves without a gap, Attributes +30, Bank +100

- **Uploaded as catalogue map #72** (HTTP 201, download SHA-256 `efb0530c…` matches; 23 versions in the family).

- Jiří (playing v3.4): "the extra spear has no animation", "fire spears are slow, sometimes miss, and hit a tower too
  far away — make it a clean multishot like X Hero Siege"; "no delay between waves, a 1 min break every 10 waves";
  "level-up +30 all stats instead of +10"; "bank +100 per minute".
- **Invisible extra spears — root cause:** the spear dummy (base Archer `earc`) was scaled to 0.01 and the Archer has
  "Scale Projectiles" (`uscb` = 1), so its spear flew at 1 % size. The dummy is now full scale with `uscb` 0 and the
  script makes it transparent (`ThrowSpear`); no corpse (`udea` 0), no sounds. The fire dummy (`dspf`, a fireball
  missile) is gone: every extra spear is the same spear, Fire Spears shows a fire burst on each spear hit.
- **Clean multishot (`SpearVolley`):** one spear per Extra Spear level at a different enemy **within the Dryad's own
  attack range (600, measured from her)** — before, targets were picked within 600 of the *target*, so a tower far
  beyond her range got hit. Spare spears go at the main target only if it survives them all (before, they flew at a
  minion that her first spear had already killed = "missed"). Her spear and the extra ones fly at 700 (was 450).
- **Waves:** the next wave starts right away when every monster is dead (`WAVE_INTERVAL` 0, "Next wave now!", no
  countdown); a **1 min** shopping break after every **10th** wave (`BREAK_EVERY`, `WAVE_BREAK` 60). `-wave` accepts 0–60.
- **Attributes** (T, from hero level 11): +30 Str/Agi/Int per level (`ATTR_PER_LEVEL`, was +10; also the automatic
  gain past level 110). **Bank:** 1 tree = +100 gold per minute (`INCOME_STEP`, was +10).
- **Verified:** pjass + build checks for the normal and the TEST build. ⚠️ **Not run in-game yet** — Jiří was playing
  (the Wine self-test needs his game closed); the spear visuals need an in-game look.

## v3.4 — 2026-11-01: 6 AoE champions, bigger waves, potions sold as power-ups

- **Uploaded as catalogue map #71** (HTTP 201, download SHA-256 `08169b93…` matches; 22 versions in the family).

- Jiří (goal): add 6 champions with AoE attacks that clean the big waves; waves +2 melee and +1 ranged per wave.
- **Champions (7 in the hall):** the Dryad + Mountain King, Tauren Chieftain, Pit Lord (melee, innate cleave 30 / 30 /
  40 %), Archmage, Lich (ranged splash missile), Far Seer (bounce to 4). Each has 3 passive skills (5 levels, `AEev`
  level holders, `AOE_CHAMPIONS` in `gen/objects.py`) of 4 kinds: bonus +20 %/lvl, blast (every hit, 20 %/lvl within
  300 of the target), nova (every 3rd hit, 40 %/lvl within 450), speed +20 %/lvl. One generic engine in the script
  (`ChampIndex`, `ChampBonusPct`, `AoeDamage`, `OnDamaged`, `OnAttacked`, `OnHeroSkill`; tables `gChamp*` / `gSk*`);
  effects run on the PRIMARY hit only (`gAtkTarget`), so native splash / bounce never multiplies them.
- **Waves:** front = 4 + 2 × wave, back = 1 × wave (`WAVE_FRONT_PER` / `WAVE_BACK_PER`), caps 30/15 → 40/20 per lane.
- **Potions:** the Apothecary now sells power-up tokens `Ipo1`–`Ipo4`: +1 charge on the carried potion, or a new potion
  in a free slot, or a refund (`GivePotion`). In-game finding: a shop refuses normal items to a full inventory but sells
  power-ups — so potions now stack even with 6 items.
- **Verified in-game (Wine, full self-test, all PASS, no crash):** wave 1 = 6 + 1, wave 2 = 8 + 2; all 7 champions in the
  hall (screenshot); each AoE champion: hits, AoE effects (MK 8, TC 21, PL 9, AM 2, Lich 8, FS 8 in the window),
  ranged native splash/bounce > primary hits (29/6, 18/6, 21/6), bonus only where a bonus skill exists, speed skills add
  hidden attack speed; Dryad: Extra Spear 5, 17 spear hits, Swift Throw, bonus; potions 1 slot × 2; premium Lv 1 → Lv 5;
  6th Fang at Lv 5 merged away with +1000 refund; Fury Gloves stay separate; XP +1 level; dead circle buy steps the price
  and is applied after the revive; remote buy while dead refused with no gold taken; full inventory: Healing Potion
  stacks to 3, a new potion type refunds; drinking heals 50 % and keeps the stack; **stress:** 4 × 60 wave-20 monsters
  on one lane, 182 killed in 19 s, game kept running; victory after every boss and all 4 gates.
- Self-test round 2 now buys the **Archmage through the tavern** (a standard hero, the real sale path) and checks the
  player-owned AoE champion fights with AoE: PASS (39 PASS, 0 FAIL in the full run). Test-only change, no new upload.

## v3.3 — 2026-11-01: premium stock 5, the double-slot shop bug, an in-game self-test

- **Uploaded as catalogue map #35** (HTTP 201 — the first upload past 20 a day, thanks to techtools-4 `9b1d3cc0`; download SHA-256 `53e1fdd5…` matches). Carries v3.0–v3.2 too.

- Jiří: premium stock 3 → **5** (`PREMIUM_STOCK`) so Lv 5 can be bought at once; and "test every feature in-game".
- **In-game test found the real shop bug:** one potion order put the **same item into two inventory slots** (then the
  stack sweep deleted it). Cause: `OnItemSold` called `UnitAddItem` although the game delivers the item right after
  the event. Now `OnItemSold` only queues sold items and `PendingTick` (0.2 s) hands over only remote buys still on the
  ground; `MergePotions` / `MergePremium` skip a duplicated handle. This was also why one premium buy could count as
  two levels and why potions "filled 2 slots".
- **Self-test:** the TEST build writes PASS/FAIL lines to `CustomMapData\TestResults\cd_test.txt` (Preload writer).
  **Verified in-game (Wine, run ≥ 170 s), all PASS:** champion = Dryad; Extra Spear Lv 5; Swift Throw 3 = hidden attack
  speed 1–3; 18 extra-spear hits; 5 fire-bonus hits; 2 Healing Potions = 1 slot × 2 charges; Mana Potion bought;
  1 Vampire Fang = Lv 1, 4 more = Lv 5; Experience buy 12 → 13; dead buy steps the price 2 → 3 and the bonus waits
  for the revive (applied 2 of 3); round 2: Level 2 gate opened, Bank income 10; no new BlizzardError crash folder.

## v3.2 — 2026-11-01: no splash on the Dryad, all spears fly together

- Jiří: remove her splash damage; she should attack with several spears at once. The splash came from the hidden fire
  orb (`Xfor`, an Orb of Fire copy) that Fire Spears added → removed; Fire Spears is now only the script bonus with a
  fire burst on the target. Extra-spear dummies wait the same 0.3 s damage point as her (`DRYAD_DAMAGE_POINT`) so all
  spears leave together, and when there are too few other enemies the spare spears hit the main target. Verified:
  pjass + build; not tried in-game.

## v3.1 — 2026-11-01: cheaper stat shop steps, bigger stat buys

- Jiří: price growth per buy +10 % → **+3 %**; Strength / Agility / Intelligence +10 → **+20**; All stats +3 → **+10**
  (`STAT_PRICE_GROWTH`, `STAT_PER_LEVEL`, `ALL_STATS_VALUE` in `gen/objects.py`). With +3 % players buy far more, so the
  price steps per kind go 40 → **100** (`STAT_TIERS`, the most the 2-digit ids allow) and the script stride 64 → 128
  (`KIND_STRIDE` / `gKindStride`). Tooltips and tips now derive the % from the constant. Map 248 → 279 KiB.
  Verified: pjass + build; not tried in-game. **Not uploaded yet** (catalogue daily limit).

## v3.0 — 2026-11-01: potions really stack

- **Not uploaded yet:** the catalogue answered HTTP 429 `UPLOAD_LIMIT` (20 uploads per uploader per rolling 24 h).

- Jiří (screenshot): buying Healing Potions filled 2 slots (3 + 3 charges). The buy-time `StackPotion` alone is not
  reliable with the neutral shop events (same class of problem as the premium merge). New `MergePotions`
  (`gen/castle_logic.j`) merges every pair of same-type potions into the first slot; it runs every 0.2 s from
  `GrabTick` and after each buy (`OnItemSold`). Verified: pjass + build; not tried in-game.

## v2.9 — 2026-11-01: Extra Spear spears fly

- **Uploaded as catalogue map #34** (HTTP 201, download SHA-256 `5758a863…` matches).

- Jiří: the number of spears must be visible by upgrade level. When the Dryad starts an attack, `OnAttacked` spawns one
  invisible locust dummy per Extra Spear level (`dspr`, or `dspf` with the fire missile once Fire Spears is learned)
  that shoots one spear at another enemy near the target; its hit makes `OnDamaged` deal the champion's last hit
  damage (`gLastHit`, + fire bonus) from the champion (kill credit stays hers). Replaces the instant extra damage.
  Verified: pjass + build; not tried in-game.

## v2.8 — 2026-11-01: slower, higher Dryad spear

- **Uploaded as catalogue map #33** (HTTP 201, download SHA-256 `7c193db7…` matches).

- Jiří: make the spear visible in flight even at short range. Missile speed 900 → 450, arc 0.15 → 0.25
  (`DRYAD_MISSILE_SPEED` / `DRYAD_MISSILE_ARC`); attack speed and damage unchanged (the hit just lands a bit later).
  Verified: build; not tried in-game.

## v2.7 — 2026-11-01: Extra Spear gets a spear icon

- **Uploaded as catalogue map #32** (HTTP 201, download SHA-256 `031dbfd8…` matches).

- Jiří (screenshot): the Extra Spear icon should be a spear → `BTNEnvenomedSpear` (`DRYAD_SKILLS`). `check_icons()` now
  also checks custom ability icons (`aart` / `arar`). Verified: build + icon check; not tried in-game.

## v2.6 — 2026-11-01: the Dryad is the only champion

- **Uploaded as catalogue map #31** (HTTP 201, download SHA-256 `3d8aacea…` matches).

- Jiří: remove all champions; add a spear-throwing deer (the Dryad) with 3 spells: one more spear per throw, attack
  speed, fire spears that raise on-hit damage. New custom hero `Edry` (Priestess of the Moon base, Dryad model, spear
  missile, `dryad_hero()` in `gen/objects.py`) is the only hero in the Hall of Champions. Skills (5 levels each,
  passive `AEev` level holders): **Q Extra Spear** +1 spear per level at another enemy within 600, full damage;
  **W Swift Throw** +20 % attack speed per level (hidden `AIsx` copies on learn); **E Fire Spears** +20 % of every hit
  as fire damage per level (+ fire missile via a hidden orb). New script damage system: enemies are registered on a
  damage trigger as they enter the map (`OnDamaged`, `DmgRebuild`, `OnEnterMap`, `OnHeroSkill`). The 6 v2.0 champions
  and the cleave ability are gone; Long Reach is no longer sold (no melee champion). Verified: pjass + build + data /
  base / icon checks; **not tried in-game** (the game was running).

## v2.5 — 2026-11-01: circle buys while dead raise the price

- **Uploaded as catalogue map #30** (HTTP 201, download SHA-256 `d5c2553a…` matches).

- Jiří: buying at the Champion's Circle while dead did not raise the price (so you could buy many at the old price).
  A dead champion never "uses" the bought tome, so the price step waited for the revive. Now `AdvanceStatPrice` counts
  every buy at once and `ApplyBought` gives the bonuses (and Experience) to the living champion (`gStatApplied`,
  `gXpPending`); `GrabTick` counts tomes at the circle or in a dead champion's inventory directly (`GrabDeadEnum`).
  Also, buys made before a champion is picked now arrive with him. Verified: pjass + build; not tried in-game.

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
