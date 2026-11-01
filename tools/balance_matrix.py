#!/usr/bin/env python3
"""What the monsters and bosses are, by wave: the game's real formulas (gen/objects.py), nothing about heroes.

    tools/balance_matrix.py [--wave 1,5,10,20,30,44]

Since v4.3 the champions have their original spells: their strength is no formula, it is measured by tools/balance_probe.py.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gen"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import objects as OB         # noqa: E402


def regulars(wave):
    return min(OB.WAVE_FRONT_BASE + OB.WAVE_FRONT_PER * wave, OB.WAVE_FRONT_MAX), min((OB.WAVE_BACK_PER * wave + 1) // 2, OB.WAVE_BACK_MAX)


def champions(wave):
    return min(wave // OB.WAVE_CHAMP_EVERY, OB.WAVE_CHAMP_MAX) if wave % OB.WAVE_CHAMP_EVERY == 0 else 0


def old_regulars(wave):
    """What a wave had up to v4.2: what the kill gold and XP of a wave are kept at."""
    return min(4 + 2 * wave, 40), min(wave, 20)


def old_hp(role_hp, wave):
    return role_hp * (1 + 0.03 * (wave - 1) ** 2)


def boss(base_hp, base_avg, wave, team=1, gate=False):
    n = wave - 1
    hp = min(1 + OB.BOSS_HP_GROWTH * n * n, OB.BOSS_HP_FACTOR_MAX)
    dmg = min(1 + OB.BOSS_DMG_GROWTH * n * n, OB.BOSS_DMG_FACTOR_MAX)
    return base_hp * hp * (OB.team_hp_factor(team) if gate else 1), base_avg * dmg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave", default="1,2,3,5,7,10,15,20,23,30,44,60")
    args = parser.parse_args()
    waves = [int(w) for w in args.wave.split(",")]
    print("| wave | melee | ranged | champions | melee HP / dmg | ranged HP / dmg | champion HP / dmg | whole wave HP | v4.2 whole wave HP | gold per kill | clear gold |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for w in waves:
        front, back = regulars(w)
        c = champions(w)
        mh, md, *_ = OB.wave_unit_combat(0, 0, 0, w, 1)
        rh, rd, *_ = OB.wave_unit_combat(0, 0, 1, w, 1)
        ch, cd, *_ = OB.wave_champion_combat(0, w, 1)
        of, ob = old_regulars(w)
        old = of * old_hp(OB.WAVE_MELEE_HP, w) + ob * old_hp(OB.WAVE_RANGED_HP, w) + (w // 10 if w % 10 == 0 else 0) * old_hp(OB.WAVE_CHAMP_HP, w)
        ratio = (of + ob) / (front + back)
        print(f"| {w} | {front} | {back} | {c} | {mh} / {md:.0f} | {rh} / {rd:.0f} | {ch} / {cd:.0f} | {front * mh + back * rh + c * ch:,} | {old:,.0f} | {round(w * ratio)} | {50 + 50 * w} |")
    print()
    rows = []
    for tier, label in ((0, "Warden"), (1, "boss")):
        base, dice, sides = OB.BOSS_DMG[tier]
        rows.append((f"Lane {label}", OB.boss_base_hp(0, tier) + OB.gear_heart_bonus(0, tier), OB._avg(OB.BOSS_DMG[tier]), False))
        for g in OB.GATE_LEVELS:
            li = g["level"] - 1
            rows.append((f"Level {g['level']} {label}", OB.boss_base_hp(li, tier) + OB.gear_heart_bonus(li, tier), int(base * g["boss"][3]) + dice * (sides + 1) / 2, True))
    print("| boss, with its Heart of Ruin | " + " | ".join(f"wave {w}: HP / a hit" for w in waves[3:]) + " |")
    print("|---|" + "---|" * len(waves[3:]))
    for name, hp, dmg, gate in rows:
        cells = []
        for w in waves[3:]:
            bh, bd = boss(hp, dmg, w, 1, gate)
            cells.append(f"{bh:,.0f} / {bd:,.0f}")
        print(f"| {name} | " + " | ".join(cells) + " |")
    gear = OB.BOSS_GEAR
    print(f"\nBosses: attack every {OB.BOSS_COOLDOWN} s, no stun holds them; gate bosses x {OB.TEAM_HP_PER_PLAYER} HP per extra player. Spell level 1 + wave / 5 + gate level, {OB.BOSS_SPELL_DAMAGE:.0f} damage per level on one target.")
    print(f"Gear, Warden / Nexus boss: Heart +{gear['heart'][0]:.0%} / +{gear['heart'][1]:.0%} base HP, Gauntlets +{gear['attack_speed'][0]:.0%} / +{gear['attack_speed'][1]:.0%} attack speed and {gear['crit_chance'][0]:.0f} / {gear['crit_chance'][1]:.0f} % chance of {gear['crit_times']:.0f}x, Warplate +{gear['armor'][0]} / +{gear['armor'][1]} armor and {gear['spell_reduction'][0]:.0%} / {gear['spell_reduction'][1]:.0%} less spell damage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
