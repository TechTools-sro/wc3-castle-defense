#!/usr/bin/env python3
"""Analytic balance matrix from the game's real tables (docs/balance.md).

    tools/balance_matrix.py [--rev GIT_REV] [--csv FILE] [--markdown]

Seven champions, four factions, waves 1/5/10/20, 1/2/4/8 players, equal-budget builds. Numbers come from ref/*.slk and
gen/objects.py of that revision. It is a MODEL: no pathing, no regeneration or healing, no level-up heal, no potions, a
fixed number of attackers and of targets per attack. Only real runs (tools/balance_probe.py) are evidence of a fight.
Assumption not checked in the engine: the script's chaos/universal extra damage ignores armor on its own (the code comment says
so, OnDamaged), and it is computed from the hit after armor. Everything is a snapshot at the START of a wave.
"""
import argparse
import csv
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from slk import read_slk  # noqa: E402

# Units\MiscGame.txt of 1.27b
STR_HP, AGI_ARMOR, AGI_BASE, AGI_SPEED, ARMOR_K = 25, 0.30, -2, 0.02, 0.06
ON_HERO = {"normal": 1.0, "pierce": 0.5, "siege": 0.5, "magic": 0.5, "chaos": 1.0, "spells": 0.7, "hero": 1.0}
HERO_ON = {"small": 1.0, "medium": 1.0, "large": 1.0, "fort": 0.5, "normal": 1.0, "hero": 1.0, "divine": 0.05, "none": 1.0}

WAVES = (1, 5, 10, 20)
PLAYERS = (1, 2, 4, 8)
MELEE_ATTACKERS = 6      # model: at most this many melee monsters reach a champion at once, all ranged ones do
AOE_TARGETS = 4          # model: other monsters near the target of a hit
FIGHT_DECAY = 0.55       # model: monsters die during the fight, the average attacker count is this share of the start
XP_PER_KILL = 25         # measured on 2026-11-01 (wave 1-6 stage 0 kills); tower-down stages give more
MAX_SPEED_FACTOR = 5.0   # the engine's attack speed limit (+400 %), not a Units\\MiscGame.txt entry: a known limit, not measured here


def load_objects(rev):
    """gen/objects.py of a revision, next to the real ref/ tables."""
    if not rev:
        base = REPO
        cleanup = None
    else:
        cleanup = tempfile.mkdtemp(prefix="balance-matrix-")
        base = Path(cleanup)
        archive = subprocess.run(["git", "-C", str(REPO), "archive", rev, "gen"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", cleanup], input=archive, check=True)
        os.symlink(REPO / "ref", base / "ref")
    sys.path.insert(0, str(base / "gen"))
    for name in ("objects", "w3files", "layout"):
        sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location("objects", base / "gen" / "objects.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["objects"] = module
    spec.loader.exec_module(module)
    sys.path.pop(0)
    if cleanup:
        shutil.rmtree(cleanup)
    return module


class Tables:
    def __init__(self):
        self.balance = read_slk(str(REPO / "ref" / "Units_UnitBalance.slk"))
        self.weapons = read_slk(str(REPO / "ref" / "Units_UnitWeapons.slk"))


def kind_key(OB, letter):
    keys = [k["key"] for k in OB.KINDS_DEF[:9]]
    return keys.index(letter)


def buy_counts(OB, budget, cycle):
    """Spends the whole budget along the cycle at the real prices. Returns {shop key: count}, spent."""
    counts = {}
    spent = 0
    i = 0
    misses = 0
    while misses < len(cycle):
        key = cycle[i % len(cycle)]
        price = OB.stat_price(counts.get(key, 0), OB.KINDS_DEF[kind_key(OB, key)].get("price", OB.STAT_BASE_PRICE))
        if spent + price <= budget and counts.get(key, 0) < OB.STAT_TIERS:
            counts[key] = counts.get(key, 0) + 1
            spent += price
            misses = 0
        else:
            misses += 1
        i += 1
    return counts, spent


def level_at(wave, OB):
    """Hero level when this wave STARTS, the same moment as gold_at: the kills of the waves before it.
    XP needed for level L is 100 x (L (L + 1) / 2 - 1). Level 2 comes with the first cleared wave anyway."""
    kills = sum(wave_size(OB, w) for w in range(1, wave))
    xp = kills * XP_PER_KILL
    level = 1
    while 100 * ((level + 1) * (level + 2) // 2 - 1) <= xp:
        level += 1
    return max(level, 2 if wave >= 2 else 1)


def wave_champions(OB, wave):
    return wave // OB.WAVE_CHAMP_EVERY if wave % OB.WAVE_CHAMP_EVERY == 0 else 0


def wave_size(OB, wave):
    return min(OB.WAVE_FRONT_BASE + OB.WAVE_FRONT_PER * wave, OB.WAVE_FRONT_MAX) + min(OB.WAVE_BACK_PER * wave, OB.WAVE_BACK_MAX) + wave_champions(OB, wave)


def gold_at(wave, OB):
    """Start gold + every cleared wave before this one + its kill gold: what a solo lane has when this wave starts."""
    gold = 1000
    for w in range(1, wave):
        gold += 50 + 50 * w + wave_size(OB, w) * w
    return gold


def hero_stats(T, OB, hero, level, counts, skills=True):
    base = {OB.DRYAD_ID: "Emoo"}.get(hero, hero)
    b, w = T.balance[base], T.weapons[base]
    kind = {k["key"]: k for k in OB.KINDS_DEF[:9]}
    value = lambda key: kind[key]["value"]
    all_stats = counts.get("F", 0) * value("F")
    strength = float(b["STR"]) + float(b["STRplus"]) * (level - 1) + counts.get("A", 0) * value("A") + all_stats
    agility = float(b["AGI"]) + float(b["AGIplus"]) * (level - 1) + counts.get("S", 0) * value("S") + all_stats
    intel = float(b["INT"]) + float(b["INTplus"]) * (level - 1) + counts.get("D", 0) * value("D") + all_stats
    primary = {"STR": strength, "AGI": agility, "INT": intel}[b["Primary"]]
    hp = float(b["HP"]) + STR_HP * strength + counts.get("Q", 0) * value("Q")
    armor = float(b["def"]) + AGI_BASE + AGI_ARMOR * agility + counts.get("R", 0) * value("R")
    damage = primary + float(w["dmgplus1"]) + float(w["dice1"]) * (float(w["sides1"]) + 1) / 2 + counts.get("E", 0) * value("E")
    speed = 1 + AGI_SPEED * agility
    # the fixed skill order of the probe: Q W E in turn, R at 6 / 11 / 16; effects from gen/objects.py
    champion = next(c for c in OB.ALL_CHAMPIONS if c[0] == hero)
    skill_list = champion[2]
    points = {"Q": 0, "W": 0, "E": 0, "R": 0}
    if skills:
        for L in range(1, level + 1):
            if L in (6, 11, 16):
                points["R"] += 1
            else:
                key = "QWE"[sum(points[k] for k in "QWE") % 3]
                if points[key] < 5:
                    points[key] += 1
    # Damage of one attack, in the code's terms (OnDamaged). hit = the attack x (1 + bonus skills), on the primary target only.
    # On the primary hit: cleave and blast go to the others; nova and storm to the target AND the others.
    # Native splash / bounce victims take the plain attack: OnDamaged returns before any bonus for them.
    # The Dryad's extra spears are worth one hit each, at other enemies first and at her target when no other is left.
    bonus = 0.0
    around = 0.0      # scripted shares of hit on the OTHER monsters near the target
    on_target = 1.0   # scripted shares of hit on the target itself
    native = 0.0      # plain attacks landing on the other monsters
    attack = w["weapTp1"]
    if hero == OB.DRYAD_ID:
        speed += 0.2 * points["W"]
        bonus += 0.2 * points["E"]
        spears = points["Q"] + points["R"] * 3 / OB.VOLLEY_EVERY
        around = min(spears, AOE_TARGETS)
        on_target += max(spears - AOE_TARGETS, 0)
        alone = 1 + spears
    else:
        around += champion[1] / 100.0 * AOE_TARGETS
        hero_row = next(a for a in OB.AOE_CHAMPIONS if a[0] == hero)
        if hero_row[1] == "splash":
            native = (0.6 + 0.3) * AOE_TARGETS / 2
        elif hero_row[1] == "bounce":
            native = 0.8 + 0.64 + 0.51
        alone = 1.0
        for (_aid, _name, key, _icon, skind, pct, _rad, _fx) in skill_list:
            lv = points[key]
            share = pct * lv / 100.0
            if skind == "bonus":
                bonus += share
            elif skind == "speed":
                speed += 0.2 * lv
            elif skind == "blast":
                around += share * AOE_TARGETS
            elif skind == "nova":
                around += share * AOE_TARGETS / 3
                on_target += share / 3
                alone += share / 3
            elif skind == "storm":
                around += share * AOE_TARGETS / OB.STORM_EVERY
                on_target += share / OB.STORM_EVERY
                alone += share / OB.STORM_EVERY
    speed = min(speed, MAX_SPEED_FACTOR)      # after every bonus, as in the code (DryadReleaseDelay)
    cooldown = float(w["cool1"]) / speed
    hit = damage * (1 + bonus)
    single = hit / cooldown
    group = (hit * (on_target + around) + damage * native) / cooldown
    return {"hp": hp, "armor": armor, "damage": damage, "cooldown": cooldown, "single_dps": single, "alone_factor": alone, "group_dps": group, "strength": strength, "agility": agility, "primary": b["Primary"], "attack": attack}


def reduction(armor):
    return armor * ARMOR_K / (1 + armor * ARMOR_K) if armor > 0 else 0.0


def monster(T, OB, arm, stage, ranged, wave, team):
    """(hp, damage, cooldown, armor, attack type) of one wave monster of that revision."""
    if hasattr(OB, "wave_unit_combat"):
        return OB.wave_unit_combat(arm, stage, ranged, wave, team)
    faction = (OB.FACTIONS + OB.GATE_LEVELS)[arm]
    unit = faction["stages"][stage][ranged]
    hp, dmg = (OB.WAVE_RANGED_HP, OB.WAVE_RANGED_DMG) if ranged else (OB.WAVE_MELEE_HP, OB.WAVE_MELEE_DMG)
    mult = OB.WAVE_STAGE_MULT[stage]
    extra_hp = faction.get("unit_hp", 0)        # v4.0 gate levels: a flat bonus
    extra_dmg = faction.get("unit_dmg", 0)
    return hp * mult + extra_hp, dmg * mult + extra_dmg, float(T.weapons[unit]["cool1"]), float(T.balance[unit]["def"]), T.weapons[unit]["atkType1"]


def champion_stats(T, OB, arm, stage, wave, team):
    if hasattr(OB, "wave_champion_combat"):
        return OB.wave_champion_combat(arm, wave, team)
    unit = (OB.FACTIONS + OB.GATE_LEVELS)[arm]["champion"]
    dmg = OB.WAVE_CHAMP_DMG
    return OB.WAVE_CHAMP_HP, dmg[0] + dmg[1] * (dmg[2] + 1) / 2, float(T.weapons[unit]["cool1"]), OB.WAVE_CHAMP_ARMOR, T.weapons[unit]["atkType1"]


def fight(T, OB, hero_stat, arm, stage, wave, team=1):
    """One champion against one lane's wave."""
    front = min(OB.WAVE_FRONT_BASE + OB.WAVE_FRONT_PER * wave, OB.WAVE_FRONT_MAX)
    back = min(OB.WAVE_BACK_PER * wave, OB.WAVE_BACK_MAX)
    m_hp, m_dmg, m_cool, m_armor, m_type = monster(T, OB, arm, stage, 0, wave, team)
    r_hp, r_dmg, r_cool, r_armor, r_type = monster(T, OB, arm, stage, 1, wave, team)
    through = 1 - reduction(hero_stat["armor"])
    melee_dps = m_dmg / m_cool * ON_HERO[m_type] * through
    ranged_dps = r_dmg / r_cool * ON_HERO[r_type] * through
    incoming = min(front, MELEE_ATTACKERS) * melee_dps + back * ranged_dps
    ehp_pool = front * m_hp / (1 - reduction(m_armor)) + back * r_hp / (1 - reduction(r_armor))
    champions = wave_champions(OB, wave)
    if champions:
        c_hp, c_dmg, c_cool, c_armor, c_type = champion_stats(T, OB, arm, stage, wave, team)
        incoming += champions * c_dmg / c_cool * ON_HERO[c_type] * through
        ehp_pool += champions * c_hp / (1 - reduction(c_armor))
    clear = ehp_pool / hero_stat["group_dps"]
    taken = incoming * FIGHT_DECAY * clear
    return {"clear_s": clear, "incoming_dps": incoming, "taken": taken, "taken_pct": 100 * taken / hero_stat["hp"], "survive_s": hero_stat["hp"] / max(incoming * FIGHT_DECAY, 0.01),
            "first_melee_hit": m_dmg * ON_HERO[m_type] * through, "first_ranged_hit": r_dmg * ON_HERO[r_type] * through}


def builds_for(primary):
    key = {"STR": "A", "AGI": "S", "INT": "D"}[primary]
    return {"mixed": "FFAS", "primary": key, "hybrid": key + "QR", "tank": "QR", "careless": "WE"}


def structure_table(OB, T):
    """(name, HP, armor, hit, cooldown, armor type, attack type) of the things a push must beat."""
    def avg(d):
        return d[0] + d[1] * (d[2] + 1) / 2.0
    rows = [("Level 1 tower", OB.TURRET_HP, OB.TURRET_ARMOR, avg(OB.TURRET_DMG), 1.3, "fort", False),
            ("Level 1 Nexus", OB.BASE_HP, OB.BASE_ARMOR, avg(OB.NEXUS_DMG), OB.NEXUS_COOLDOWN, "fort", False),
            ("Lane boss", OB.BOSS_HP[1], OB.BOSS_ARMOR[1], avg(OB.BOSS_DMG[1]), 1.6, "hero", False)]
    for g in OB.GATE_LEVELS:
        rows.append((f"L{g['level']} tower", g["tower"][0], g["tower"][1], avg(g["tower"][2]), 1.3, "fort", True))
        rows.append((f"L{g['level']} Nexus", g["nexus"][0], g["nexus"][1], avg(g["nexus"][2]), OB.NEXUS_COOLDOWN, "fort", True))
        boss = g["boss"]
        # the object data: base x level factor, dice unchanged
        base, dice, sides = OB.BOSS_DMG[1]
        rows.append((f"L{g['level']} boss", OB.BOSS_HP[1] * boss[2], OB.BOSS_ARMOR[1] + 2 * g["level"], avg((int(base * boss[3]), dice, sides)), 1.6, "hero", True))
    return rows


def team_factor(OB, team):
    return OB.team_hp_factor(team) if hasattr(OB, "team_hp_factor") else 1.0


def attainment(T, OB, hero, cycle, team, max_wave=80, lives=3):
    """For every push target: the first wave whose gold and level allow it, as a bracket (low, high).
    high = cautious: the whole team's damage for the lives of ONE champion. low = optimistic: all champions keep hitting while the
    target works through all their lives. Both are bounds of a model with gold spent only on stats, no proven earliest wave."""
    out = {}
    for name, hp, armor, hit, cooldown, armor_type, shared in structure_table(OB, T):
        target_hp = hp * (team_factor(OB, team) if shared else 1.0)
        teammates = team if shared else 1
        low = high = None
        for wave in range(1, max_wave + 1):
            counts, _ = buy_counts(OB, gold_at(wave, OB), cycle)
            stat = hero_stats(T, OB, hero, level_at(wave, OB), counts)
            dps = stat["single_dps"] * stat["alone_factor"] * HERO_ON[armor_type] * (1 - reduction(armor))
            life = stat["hp"] / (hit / cooldown * (1 - reduction(stat["armor"])))
            if low is None and dps * teammates * life * lives * teammates >= target_hp:
                low = wave
            if high is None and dps * teammates * life * lives >= target_hp:
                high = wave
            if high is not None:
                break
        out[name] = (low, high)
    return out


def matrix(rev=None):
    OB = load_objects(rev)
    T = Tables()
    rows = []
    for hero in OB.ALL_HEROES:
        base = {OB.DRYAD_ID: "Emoo"}.get(hero, hero)
        name = T.balance[base]["comment(s)"] if "comment(s)" in T.balance[base] else hero
        primary = T.balance[base]["Primary"]
        for build, cycle in builds_for(primary).items():
            for wave in WAVES:
                budget = gold_at(wave, OB)
                level = level_at(wave, OB)
                counts, spent = buy_counts(OB, budget, cycle)
                stat = hero_stats(T, OB, hero, level, counts)
                for arm, faction in enumerate(OB.FACTIONS):
                    for stage in (0,):
                        f = fight(T, OB, stat, arm, stage, wave)
                        rows.append({"hero": hero, "name": name, "build": build, "wave": wave, "faction": faction["name"], "stage": stage, "level": level, "budget": budget, "spent": spent,
                                     "hp": round(stat["hp"]), "armor": round(stat["armor"], 1), "single_dps": round(stat["single_dps"]), "group_dps": round(stat["group_dps"]),
                                     "clear_s": round(f["clear_s"], 1), "incoming_dps": round(f["incoming_dps"]), "taken_pct": round(f["taken_pct"]), "survive_s": round(f["survive_s"], 1)})
    return OB, T, rows


def print_summary(OB, T, rows):
    print("### Fight model: share of the champion's HP lost clearing one wave (first number) and seconds to clear it (second).")
    print("Stage 0, solo lane, gold and level the lane has reached by that wave. Worst and best over the four factions.\n")
    builds = sorted({r["build"] for r in rows})
    for wave in WAVES:
        print(f"**Wave {wave}** (budget {gold_at(wave, OB)} g, model level {level_at(wave, OB)}, {wave_size(OB, wave)} monsters per lane)\n")
        print("| champion | " + " | ".join(builds) + " |")
        print("|---|" + "---|" * len(builds))
        for hero in OB.ALL_HEROES:
            cells = []
            for build in builds:
                sel = [r for r in rows if r["hero"] == hero and r["build"] == build and r["wave"] == wave]
                cells.append(f"{min(r['taken_pct'] for r in sel)}-{max(r['taken_pct'] for r in sel)} % / {min(r['clear_s'] for r in sel):.0f}-{max(r['clear_s'] for r in sel):.0f} s")
            print(f"| {hero} | " + " | ".join(cells) + " |")
        print()
    print("### Factions: incoming DPS on the same mixed-build Dryad, stage 0\n")
    print("| wave | " + " | ".join(f["name"] for f in OB.FACTIONS) + " |")
    print("|---|" + "---|" * len(OB.FACTIONS))
    for wave in WAVES:
        vals = [next(r for r in rows if r["hero"] == OB.DRYAD_ID and r["build"] == "mixed" and r["wave"] == wave and r["faction"] == f["name"])["incoming_dps"] for f in OB.FACTIONS]
        print(f"| {wave} | " + " | ".join(str(v) for v in vals) + " |")
    print()
    print("### First wave where the push targets can fall (mixed build, 3 lives each). A bracket of a model, optimistic-cautious, not a proven earliest wave\n")
    targets = [r[0] for r in structure_table(OB, T)]
    print("| players | champion | " + " | ".join(targets) + " |")
    print("|---|---|" + "---|" * len(targets))
    for team in PLAYERS:
        for hero in (OB.ALL_HEROES[0], OB.ALL_HEROES[1], OB.ALL_HEROES[4]):
            got = attainment(T, OB, hero, "FFAS", team)
            cell = lambda g: f"{g[0] or '>80'}-{g[1] or '>80'}" if g[0] != g[1] else str(g[0] or ">80")
            print(f"| {team} | {hero} | " + " | ".join(cell(got[t]) for t in targets) + " |")
    print()


def print_stages(OB, T):
    print("### Tower and Nexus down: the same wave on stage 0 / 1 / 2 (mixed build, Scourge). Share of HP lost, seconds to clear; a model\n")
    print("| wave | champion | stage 0 | stage 1 | stage 2 |")
    print("|---|---|---|---|---|")
    for wave in (10, 20, 30):
        counts, _ = buy_counts(OB, gold_at(wave, OB), "FFAS")
        for hero in (OB.ALL_HEROES[0], OB.ALL_HEROES[1], OB.ALL_HEROES[4]):
            stat = hero_stats(T, OB, hero, level_at(wave, OB), counts)
            cells = []
            for stage in (0, 1, 2):
                f = fight(T, OB, stat, 0, stage, wave)
                cells.append(f"{f['taken_pct']:.0f} % / {f['clear_s']:.0f} s")
            print(f"| {wave} | {hero} | " + " | ".join(cells) + " |")
    print()


def print_late(OB, T):
    print("### Late waves: mixed build, Scourge, stage 0 and stage 2. Share of HP lost, seconds to clear; a model\n")
    heroes = (OB.ALL_HEROES[0], OB.ALL_HEROES[1], OB.ALL_HEROES[4], OB.ALL_HEROES[6])
    print("| wave | gold | level | " + " | ".join(f"{hero} | {hero} stage 2" for hero in heroes) + " |")
    print("|---|---|---|" + "---|---|" * len(heroes))
    for wave in (30, 40, 50, 60, 70):
        counts, _ = buy_counts(OB, gold_at(wave, OB), "FFAS")
        cells = []
        for hero in heroes:
            stat = hero_stats(T, OB, hero, level_at(wave, OB), counts)
            for stage in (0, 2):
                f = fight(T, OB, stat, 0, stage, wave)
                cells.append(f"{f['taken_pct']:.0f} % / {f['clear_s']:.0f} s")
        print(f"| {wave} | {gold_at(wave, OB)} | {level_at(wave, OB)} | " + " | ".join(cells) + " |")
    print()


def print_budget(OB, T):
    print("### Spending less: the same wave with a share of its gold spent, mixed build, Scourge, stage 0. Share of HP lost, seconds to clear; a model\n")
    shares = (1.0, 0.75, 0.5, 0.25)
    print("| wave | champion | " + " | ".join(f"{int(s * 100)} % of the gold" for s in shares) + " |")
    print("|---|---|" + "---|" * len(shares))
    for wave in (5, 10, 20):
        for hero in (OB.ALL_HEROES[0], OB.ALL_HEROES[1], OB.ALL_HEROES[4]):
            cells = []
            for share in shares:
                counts, _ = buy_counts(OB, int(gold_at(wave, OB) * share), "FFAS")
                f = fight(T, OB, hero_stats(T, OB, hero, level_at(wave, OB), counts), 0, 0, wave)
                cells.append(f"{f['taken_pct']:.0f} % / {f['clear_s']:.0f} s")
            print(f"| {wave} | {hero} | " + " | ".join(cells) + " |")
    print()


def print_shared(OB, T):
    print("### A shared gate wave, the whole team on it (mixed build, Dryad's stats for everyone, stage 0, seconds to clear; share of one champion's HP lost). A model: a real team also holds its own lanes\n")
    print("| wave | gate level | " + " | ".join(f"{team} players" for team in PLAYERS) + " |")
    print("|---|---|" + "---|" * len(PLAYERS))
    for wave in (15, 25):
        counts, _ = buy_counts(OB, gold_at(wave, OB), "FFAS")
        stat = hero_stats(T, OB, OB.ALL_HEROES[0], level_at(wave, OB), counts)
        for gate in (OB.GATE_LEVELS[0], OB.GATE_LEVELS[-1]):
            cells = []
            for team in PLAYERS:
                f = fight(T, OB, stat, gate["arm"], 0, wave, team)
                clear = f["clear_s"] / team
                cells.append(f"{clear:.0f} s, {100 * f['incoming_dps'] * FIGHT_DECAY * clear / stat['hp']:.0f} %")
            print(f"| {wave} | L{gate['level']} | " + " | ".join(cells) + " |")
    print()


def print_final(OB, T):
    grows_with_percent = not hasattr(OB, "wave_unit_combat")       # v4.0 kept his HP percentage when he grew
    print("### The final boss: seconds to kill him if every champion keeps hitting (mixed build, Dryad's stats for everyone), and seconds one champion lives under him. A model\n")
    print("| team gold of wave | minute | " + " | ".join(f"{team} players" for team in PLAYERS) + " | one life |")
    print("|---|---|" + "---|" * len(PLAYERS) + "---|")
    for wave, minute in ((25, 15), (30, 20), (40, 30), (40, 50)):
        counts, _ = buy_counts(OB, gold_at(wave, OB), "FFAS")
        stat = hero_stats(T, OB, OB.ALL_HEROES[0], level_at(wave, OB), counts)
        armor = OB.FINAL_ARMOR_BASE + minute // OB.FINAL_ARMOR_EVERY
        dps = stat["single_dps"] * stat["alone_factor"] * HERO_ON["hero"] * (1 - reduction(armor))
        hit = OB.FINAL_DMG_BASE + OB.FINAL_DMG_PER_MIN * minute
        life = stat["hp"] / (hit / 1.2 * (1 - reduction(stat["armor"])))
        cells = []
        for team in PLAYERS:
            factor = 3 if team >= 6 else 2 if team >= 3 else 1
            hp = (OB.FINAL_HP_BASE + OB.FINAL_HP_PER_MIN * minute) * factor
            regen = OB.FINAL_REGEN + (OB.FINAL_HP_PER_MIN * factor / 60 * 0.5 if grows_with_percent else 0.0)
            net = team * dps - regen
            cells.append(f"{hp / net:.0f} s" if net > 0 else "never")
        print(f"| {wave} | {minute} | " + " | ".join(cells) + f" | {life:.0f} s |")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rev", help="git revision (default: the working tree)")
    parser.add_argument("--csv")
    args = parser.parse_args()
    OB, T, rows = matrix(args.rev)
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print_summary(OB, T, rows)
    print_stages(OB, T)
    print_late(OB, T)
    print_budget(OB, T)
    print_shared(OB, T)
    print_final(OB, T)
    return 0


if __name__ == "__main__":
    sys.exit(main())
