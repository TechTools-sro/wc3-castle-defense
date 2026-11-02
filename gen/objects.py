"""Custom objects (war3map.w3u / war3map.w3t) + wave rosters, v2 (hero lane defense).

Field ids / value types verified against Units\\UnitMetaData.slk of 1.27:
int=0, real=1, unreal=2, string-ish (string, model, icon, lists, armor/attack type)=3.
"""
from w3files import VT_INT as I, VT_REAL as R, VT_UNREAL as U, VT_STRING as S
import re

import xhs_data as XHS
from xhs_text import SKILLS as XHS_SKILLS, HERO_TIPS as XHS_TIPS
import xhs_tips as TIPS

FACTIONS = [
    {   # North
        "name": "The Scourge", "color": "|cff80c0ff",
        "base": ("unp2", "Scourge Nexus"),
        "turret": ("uzg1", "Frost Spire"),
        "boss": {"base": "nsrw", "name": "Vexmoor the Lich Lord", "scale": 2.1, "range": 600,
                 "model": "units\\undead\\HeroLich\\HeroLich.mdl",
                 "icon": "ReplaceableTextures\\CommandButtons\\BTNLichVersion2.blp",
                 "missile": "Abilities\\Weapons\\LichMissile\\LichMissile.mdl",
                 "sound": "HeroLich", "abils": "ACfn,ACbz",
                 "cast1": ("frostnova", 1), "cast2": ("blizzard", 2), "summon": ("nske", 3)},
        "tiers": [("nske", "nska"), ("ugho", "nskm"), ("nsko", "ucry"),
                  ("nsog", "ngh2"), ("uabo", "ufro"), ("nsoc", "ufro")],
        "stages": [("nske", "nska"), ("nsko", "ucry"), ("uabo", "ufro")],
        "champion": "nrvd",
    },
    {   # East
        "name": "The Burning Legion", "color": "|cff60ff60",
        "base": ("ndmg", "Legion Nexus"),
        "turret": ("ntx2", "Hellfire Tower"),
        "boss": {"base": "ninf", "name": "Azgaroth the Pit Lord", "scale": 1.8, "range": 128,
                 "model": "units\\demon\\PitLord\\PitLord.mdl",
                 "icon": "ReplaceableTextures\\CommandButtons\\BTNPitLord.blp",
                 "sound": "PitLord", "abils": "Awrs,ACrf,ACce",
                 "cast1": ("stomp", 0), "cast2": ("rainoffire", 2), "summon": ("npfl", 2)},
        "tiers": [("nfgu", "nsat"), ("npfl", "nsts"), ("nfgb", "ners"),
                  ("nfel", "nerd"), ("npfm", "nerw"), ("ninf", "nbal")],
        "stages": [("nfgu", "nsat"), ("nfgb", "ners"), ("npfm", "nerw")],
        "champion": "nina",
    },
    {   # South
        "name": "The Tidal Horde", "color": "|cff40e0d0",
        "base": ("nntt", "Abyssal Nexus"),
        "turret": ("nntg", "Abyssal Guardian"),
        "boss": {"base": "nnrg", "name": "Nazreth the Tidelord", "scale": 2.1, "range": 128,
                 "abils": "ACcv,Awrs,ACbh",
                 "cast1": ("carrionswarm", 2), "cast2": ("stomp", 0), "summon": ("nmmu", 2)},
        "tiers": [("nmrl", "ntrh"), ("nnmg", "nsnp"), ("nmyr", "ntrt"),
                  ("nmmu", "nsel"), ("nnrg", "nhyc"), ("ntrd", "nehy")],
        "stages": [("nmrl", "ntrh"), ("nmyr", "ntrt"), ("nnrg", "nhyc")],
        "champion": "nlrv",
    },
    {   # West
        "name": "The Wildland Clans", "color": "|cffd2a060",
        "base": ("ofrt", "Clan Nexus"),
        "turret": ("owtw", "Clan Watchtower"),
        "boss": {"base": "nogl", "name": "Gorgoth the Ogre Warlord", "scale": 2.5, "range": 128,
                 "abils": "ACsh,ACtc,ACbh",
                 "cast1": ("shockwave", 2), "cast2": ("creepthunderclap", 0), "summon": ("nogr", 2)},
        "tiers": [("ngno", "ngna"), ("nogr", "nftr"), ("ncen", "nftb"),
                  ("nogm", "ncks"), ("nogl", "nftk"), ("nmgd", "nsrw")],
        "stages": [("ngno", "ngna"), ("ncen", "nftb"), ("nogl", "nftk")],
        "champion": "nggr",
    },
]

# Gate levels 2-5 (shared lanes 8-11 = arms 4-7). Each opens when the previous level's Nexus falls (Level 2: the
# first player Nexus). Higher level = harder: tower, Nexus, wave bonus HP/damage, boss, gold.
#   nexus/tower = (HP, armor, (dmg base, dice, sides)); unit_hp/unit_dmg = bonus on every wave unit (and Protector);
#   v3.9 (Jiri): every tower and Nexus damage x10 and HP x5; "the better the building, the more damage": each Nexus hits
#   ~10 % harder than its own tower and every level harder than the one before (build-time check: building_ladder)
#   boss = (source faction index for model + spells, name, HP multiplier, damage multiplier, scale)
GATE_LEVELS = [
    {"level": 2, "lane": 8, "arm": 4, "name": "The Dark Gate", "color": "|cffff4040", "dir": "north-east",
     "base": ("unp2", "Dark Citadel"), "turret": ("uzg1", "Dark Spire"),
     "stages": [("uabo", "ngh2"), ("ninf", "nbal"), ("ninf", "nbal")], "champion": "nrvd",
     "nexus": (40000, 15, (38400, 4, 50)), "tower": (32500, 8, (34995, 1, 10)), "tint": (255, 90, 90),
     "gold": 500, "nexus_scale": 1.2, "tower_scale": 1.5,
     "boss": (0, "Malgrath the Dark Lich", 3, 1.5, 2.4)},
    {"level": 3, "lane": 9, "arm": 5, "name": "The Frozen Gate", "color": "|cff80dfff", "dir": "north-west",
     "base": ("uaod", "Frozen Throne"), "turret": ("uzg1", "Frozen Spire"),
     "stages": [("nsoc", "ufro"), ("ninf", "nbal"), ("ninf", "nbal")], "champion": "nlrv",
     "nexus": (75000, 20, (49400, 4, 50)), "tower": (50000, 12, (44995, 1, 10)), "tint": (140, 200, 255),
     "gold": 1000, "nexus_scale": 1.6, "tower_scale": 1.7,
     "boss": (2, "Kel'Thar the Frozen Tide", 5, 2.0, 2.5)},
    {"level": 4, "lane": 10, "arm": 6, "name": "The Shadow Gate", "color": "|cffc080ff", "dir": "south-west",
     "base": ("ndmg", "Shadow Portal"), "turret": ("ntx2", "Shadow Spire"),
     "stages": [("ninf", "nerw"), ("ninf", "nhyc"), ("ninf", "nhyc")], "champion": "nina",
     "nexus": (125000, 25, (65900, 4, 50)), "tower": (75000, 15, (59995, 1, 10)), "tint": (200, 120, 255),
     "gold": 2000, "nexus_scale": 1.4, "tower_scale": 1.6,
     "boss": (1, "Azgaroth the Shadow Lord", 8, 3.0, 2.2)},
    {"level": 5, "lane": 11, "arm": 7, "name": "The Inferno Gate", "color": "|cffff9020", "dir": "far south-west",
     "base": ("ofrt", "Inferno Fortress"), "turret": ("owtw", "Inferno Tower"),
     "stages": [("nrvd", "ufro"), ("nlrv", "nbal"), ("nlrv", "nbal")], "champion": "nggr",
     "nexus": (200000, 30, (87900, 4, 50)), "tower": (105000, 18, (79995, 1, 10)), "tint": (255, 160, 60),
     "gold": 3000, "nexus_scale": 1.4, "tower_scale": 1.8,
     "boss": (1, "Infernus the World Breaker", 12, 4.0, 2.8)},
]
GATE_ARMS = [g["arm"] for g in GATE_LEVELS]

# Standardized wave units (v4.1, Jiri: stronger monsters, predictable scaling). Every faction's units are copies with the
# same combat values: only the model differs. Melee role = the front line, ranged role = the back line.
WAVE_MELEE_HP, WAVE_MELEE_DMG = 700, 60
WAVE_RANGED_HP, WAVE_RANGED_DMG = 420, 120
WAVE_MELEE_COOLDOWN, WAVE_RANGED_COOLDOWN = 1.5, 1.8
WAVE_MELEE_ARMOR, WAVE_RANGED_ARMOR = 2, 0
WAVE_MELEE_RANGE, WAVE_RANGED_RANGE = 100, 500
WAVE_ATTACK_TYPE, WAVE_SPEED = "normal", 270
WAVE_TARGETS = "ground,structure,debris,item,ward"     # attack 1 of every wave monster (some models keep the ground attack in attack 2)
# Only the movement type stays the model's own: a few fly or hover (frost wyrms, banshees, revenants) or swim (nagas). Everything else is equal.
WAVE_SAME = [("uaen", I, 1), ("ua1t", S, WAVE_ATTACK_TYPE), ("ua1g", S, WAVE_TARGETS), ("umvs", I, WAVE_SPEED), ("uabi", S, ""),
             ("uhpr", U, 0.0), ("uhrt", S, "none"), ("udty", S, "medium"),
             ("udea", I, 3)]   # v4.3: every monster leaves a corpse that can rise (the Crypt Lord's beetles); it decays by itself
WAVE_STAGE_HP = [1.0, 1.5, 2.0]        # stage 1 = tower down, stage 2 = Nexus down
WAVE_STAGE_DMG = [1.0, 1.25, 1.5]
# Growth by the wave number, n = wave - 1: HP x (1 + WAVE_HP_GROWTH n^2), damage x (1 + WAVE_DMG_GROWTH n^2). HP grows faster.
# v4.3 (Jiri: too many weak monsters, against far stronger champions): fewer of them and three times the growth.
WAVE_HP_GROWTH, WAVE_DMG_GROWTH = 0.092, 0.045
# Gate levels 2-5: +25 % HP and +10 % damage per level above 1. Only shared obstacles scale with the team, mainly in HP.
GATE_HP_PER_LEVEL, GATE_DMG_PER_LEVEL = 0.25, 0.10
TEAM_HP_PER_PLAYER = 0.35              # shared gates: HP x (1 + 0.35 (team - 1)); team = champions at the start of the round
# The Bank pays a player for at most this many seconds per wave of his lane, renewed only by his next wave: 2 payments at most, however long a wave is held.
INCOME_WAVE_SECONDS = 120
# Scaling goes through hidden item-bonus abilities, one per bit.
# A bonus above the last bit stays at the maximum (saturates, never wraps): +13 107 100 HP, +81 915 damage.
SCALE_HP_BITS, SCALE_HP_STEP = 17, 100
SCALE_DMG_BITS, SCALE_DMG_STEP = 14, 5


def wave_hp_factor(wave):
    return 1.0 + WAVE_HP_GROWTH * (wave - 1) ** 2


def wave_dmg_factor(wave):
    return 1.0 + WAVE_DMG_GROWTH * (wave - 1) ** 2


def team_hp_factor(team):
    return 1.0 + TEAM_HP_PER_PLAYER * (team - 1)


def scaled_value(base, factor, step, bits):
    """What the script gives a unit: the bonus rounded down to its step, at most the top of the bits."""
    steps = min(int(base * (factor - 1.0)) // step, (1 << bits) - 1)
    return base + steps * step


SCALE_ID_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"


def scale_bit_ids():
    return [f"Xwh{SCALE_ID_CHARS[i]}" for i in range(SCALE_HP_BITS)] + [f"Xwd{SCALE_ID_CHARS[i]}" for i in range(SCALE_DMG_BITS)]


def scale_abilities():
    out = [("AIlf", f"Xwh{SCALE_ID_CHARS[i]}", [("Ilif", I, 1, 1, SCALE_HP_STEP << i)]) for i in range(SCALE_HP_BITS)]
    out += [("AIat", f"Xwd{SCALE_ID_CHARS[i]}", [("Iatt", I, 1, 1, SCALE_DMG_STEP << i)]) for i in range(SCALE_DMG_BITS)]
    return out


def wave_unit_combat(arm, stage, ranged, wave, team):
    """(HP, damage, cooldown, armor, attack type) of one wave monster: the numbers the script produces. Arms 4-7 are gate levels."""
    hp, dmg = (WAVE_RANGED_HP, WAVE_RANGED_DMG) if ranged else (WAVE_MELEE_HP, WAVE_MELEE_DMG)
    gate_hp = gate_dmg = 1.0
    if arm >= len(FACTIONS):
        above = arm - len(FACTIONS) + 1
        gate_hp = (1 + GATE_HP_PER_LEVEL * above) * team_hp_factor(team)
        gate_dmg = 1 + GATE_DMG_PER_LEVEL * above
    return (scaled_value(hp * WAVE_STAGE_HP[stage], wave_hp_factor(wave) * gate_hp, SCALE_HP_STEP, SCALE_HP_BITS),
            scaled_value(dmg * WAVE_STAGE_DMG[stage], wave_dmg_factor(wave) * gate_dmg, SCALE_DMG_STEP, SCALE_DMG_BITS),
            WAVE_RANGED_COOLDOWN if ranged else WAVE_MELEE_COOLDOWN, WAVE_RANGED_ARMOR if ranged else WAVE_MELEE_ARMOR, WAVE_ATTACK_TYPE)


def wave_champion_combat(arm, wave, team):
    gate_hp = gate_dmg = 1.0
    if arm >= len(FACTIONS):
        above = arm - len(FACTIONS) + 1
        gate_hp = (1 + GATE_HP_PER_LEVEL * above) * team_hp_factor(team)
        gate_dmg = 1 + GATE_DMG_PER_LEVEL * above
    base = WAVE_CHAMP_DMG[0] + WAVE_CHAMP_DMG[1] * (WAVE_CHAMP_DMG[2] + 1) / 2
    return (scaled_value(WAVE_CHAMP_HP, wave_hp_factor(wave) * gate_hp, SCALE_HP_STEP, SCALE_HP_BITS),
            scaled_value(base, wave_dmg_factor(wave) * gate_dmg, SCALE_DMG_STEP, SCALE_DMG_BITS), WAVE_MELEE_COOLDOWN, WAVE_CHAMP_ARMOR, WAVE_ATTACK_TYPE)


def check_scaling():
    """Fails the build if a wave monster ever got weaker with the wave, or the bits run out before wave 80 for the strongest
    monster of any role (Level 5, stage 2, 8 players): compared before the saturation, which would hide it."""
    for arm in (0, len(FACTIONS) + len(GATE_LEVELS) - 1):
        for stage in range(3):
            for ranged in (0, 1):
                for team in (1, 8):
                    last = (0, 0)
                    for wave in range(1, 151):
                        hp, dmg, *_ = wave_unit_combat(arm, stage, ranged, wave, team)
                        assert hp >= last[0] and dmg >= last[1], (arm, stage, ranged, wave, team)
                        last = (hp, dmg)
    above = len(GATE_LEVELS)
    hp_factor = wave_hp_factor(80) * (1 + GATE_HP_PER_LEVEL * above) * team_hp_factor(8)
    dmg_factor = wave_dmg_factor(80) * (1 + GATE_DMG_PER_LEVEL * above)
    champion_dmg = WAVE_CHAMP_DMG[0] + WAVE_CHAMP_DMG[1] * (WAVE_CHAMP_DMG[2] + 1) / 2
    for base_hp, base_dmg in ((WAVE_MELEE_HP * WAVE_STAGE_HP[2], WAVE_MELEE_DMG * WAVE_STAGE_DMG[2]),
                              (WAVE_RANGED_HP * WAVE_STAGE_HP[2], WAVE_RANGED_DMG * WAVE_STAGE_DMG[2]), (WAVE_CHAMP_HP, champion_dmg)):
        assert int(base_hp * (hp_factor - 1)) // SCALE_HP_STEP < (1 << SCALE_HP_BITS), base_hp
        assert int(base_dmg * (dmg_factor - 1)) // SCALE_DMG_STEP < (1 << SCALE_DMG_BITS), base_dmg


def wave_unit_id(arm, stage, ranged):      # q<arm><stage><m|r>, e.g. q00m = Scourge stage-0 melee
    return f"q{arm}{stage}{'r' if ranged else 'm'}"


# Wave size (same for every lane and stage): front line = melee, back line = ranged.
# v4.3 (Jiri: far too many weak monsters): at most 16 + 8 + 6 champions, each far stronger. The first wave is the same 6 + 1.
WAVE_FRONT_BASE = 5          # front = 5 + wave  (wave 1 -> 6)
WAVE_FRONT_PER = 1
WAVE_BACK_PER = 1            # back  = (wave + 1) / 2  (wave 1 -> 1, wave 3 -> 2)
WAVE_FRONT_MAX, WAVE_BACK_MAX = 16, 8
WAVE_CHAMP_MAX = 6
# Champions join every 10th wave: wave 10 -> 1, wave 20 -> 2, ... per lane, as weakened copies (nc{d}0).
WAVE_CHAMP_EVERY = 10
WAVE_CHAMP_HP, WAVE_CHAMP_ARMOR, WAVE_CHAMP_DMG, WAVE_CHAMP_SCALE = 2100, 3, (89, 1, 1), 1.0     # v4.1: three melee HP, 1.5 melee damage

# Champions (v4.3, Jiri): twelve champions of X Hero Siege 3.28 in the one tavern, with their real abilities. Their object data is copied as it
# is (gen/xhs_data.py, generated by tools/xhs_port.py), the text is ours (gen/xhs_text.py), the few triggers they need are in the script (HeroGlue).
FX = {"final": "Abilities\\Spells\\Demon\\DarkPortal\\DarkPortalTarget.mdl", "": ""}
DRYAD_ID = "H007"
ALL_HEROES = [h for h, _skills in XHS.ROSTER]
# A premium item with the same code stops a hero learning a NATIVE ability id for good (Stormhammer and Bash, Axe and Critical Strike, seen in hidden runs; the Dryad's custom copies learn fine).
# So these three learnables get ids of their own, with the reference's data as it is: nothing else about them changes.
LEARN_REMAP = {"AHbh": "Xhbh", "AOcr": "Xhcr", "AEev": "Xhev"}
LEARN_ORIGIN = {new: old for old, new in LEARN_REMAP.items()}
HERO_SKILLS = {h: [LEARN_REMAP.get(a, a) for a in skills] for h, skills in XHS.ROSTER}
for _old, _new in LEARN_REMAP.items():
    XHS_SKILLS[_new] = XHS_SKILLS[_old]
SKILLS_PER_HERO = 5
SKILL_KEYS = "QWERT"
INNATE_KEY, GRANT_KEY = "D", "F"
TAVERN_KEYS = "QWERASDFZXCV"
TAVERNS = [("tvc0", "Hall of Champions", ALL_HEROES)]
assert len(ALL_HEROES) == 12 and all(len(s) == SKILLS_PER_HERO for s in HERO_SKILLS.values())

# Premium Armory (secret grove): 8 simple, special items for 1000 gold each. Each = a real base item (class/model)
# + one custom ability cloned from a real item ability with a stronger value.
#   (item id, base item, name, effect line, icon, ability base, ability id, [(field, type, data ptr, value)])
PREMIUM_PRICE = 1000
# Upgradable: buying an item you already hold merges both into the next level (Lv 1..PREMIUM_LEVELS).
# Each level = its own item type + ability with stronger values; only Lv 1 is sold.
PREMIUM_LEVELS = 5
PREMIUM_STOCK = 5            # = PREMIUM_LEVELS, so Lv 5 can be bought in one go (v3.3, Jiri; was 3)
# v4.4 (Jiri: grossly overtuned, 30 % lifesteal for 1000 gold): the bonus a rank gives in all, not on top of the rank before. Modest starter values, the highest
# in line with parts of X Hero Siege's own far dearer items or the native item they copy. Not a measured economy.
PREMIUM_FANG = (5, 10, 15, 20, 30)
PREMIUM_GLOVES = (5, 10, 15, 20, 25)
PREMIUM_AXE = (4, 8, 12, 16, 20)
PREMIUM_AXE_TIMES = 2
PREMIUM_HAMMER = (3, 6, 9, 12, 15)
PREMIUM_HAMMER_DAMAGE = (5, 10, 15, 20, 25)
PREMIUM_HAMMER_STUN = 0.5
PREMIUM_CLOAK = (3, 6, 9, 12, 15)
PREMIUM_BOOTS = (10, 20, 30, 40, 50)
PREMIUM_HEART = (2, 4, 6, 8, 10)
PREMIUM_MASK = (10, 20, 30, 40, 50)
# (name, base item, icon, ability base, [(field, type, data ptr)], values(L), what it does, [(label, the value each rank shows)])
PREMIUM_DEF = [
    ("Vampire Fang", "modt", "BTNMaskOfDeath", "AIva", [("Ivam", "U", 1)], lambda L: [PREMIUM_FANG[L - 1] / 100.0],
     "Your attacks heal you by a share of their damage.", [("Lifesteal", [f"{v}%" for v in PREMIUM_FANG])]),
    ("Fury Gloves", "gcel", "BTNGlove", "AIsx", [("Isx1", "U", 1)], lambda L: [PREMIUM_GLOVES[L - 1] / 100.0],
     "You attack faster.", [("Attack speed", [f"+{v}%" for v in PREMIUM_GLOVES])]),
    ("Executioner's Axe", "ratc", "BTNCriticalStrike", "AIcs", [("Ocr1", "U", 1), ("Ocr2", "U", 2), ("Ocr3", "U", 3), ("Ocr4", "U", 4)],
     lambda L: [float(PREMIUM_AXE[L - 1]), float(PREMIUM_AXE_TIMES), 0.0, 0.0],
     f"A chance of an attack with {PREMIUM_AXE_TIMES}x damage.", [("Chance", [f"{v}%" for v in PREMIUM_AXE])]),
    ("Stormhammer", "ratc", "BTNBash", "AIbx", [("Hbh1", "U", 1), ("Hbh3", "U", 3), ("adur", "U", 0), ("ahdu", "U", 0)],
     lambda L: [float(PREMIUM_HAMMER[L - 1]), float(PREMIUM_HAMMER_DAMAGE[L - 1]), PREMIUM_HAMMER_STUN, PREMIUM_HAMMER_STUN],
     f"A chance of bonus damage and a {PREMIUM_HAMMER_STUN} s stun.", [("Chance", [f"{v}%" for v in PREMIUM_HAMMER]), ("Damage", [f"+{v}" for v in PREMIUM_HAMMER_DAMAGE])]),
    ("Phantom Cloak", "evtl", "BTNEvasion", "AIev", [("Eev1", "U", 1)], lambda L: [PREMIUM_CLOAK[L - 1] / 100.0],
     "Attacks against you miss.", [("Dodge", [f"{v}%" for v in PREMIUM_CLOAK])]),
    ("Winged Boots", "bspd", "BTNBootsOfSpeed", "AIms", [("Imvb", "I", 1)], lambda L: [PREMIUM_BOOTS[L - 1]],
     "You move faster.", [("Move speed", [f"+{v}" for v in PREMIUM_BOOTS])]),
    ("Troll Heart", "rlif", "BTNRegenerate", "Arel", [("Ihpr", "I", 1)], lambda L: [PREMIUM_HEART[L - 1]],
     "You heal over time.", [("HP per second", [f"+{v}" for v in PREMIUM_HEART])]),
    ("Arcane Mask", "rwiz", "BTNSobiMask", "AIrm", [("Imrp", "U", 1)], lambda L: [PREMIUM_MASK[L - 1] / 100.0],
     "Your mana comes back faster.", [("Mana regeneration", [f"+{v}%" for v in PREMIUM_MASK])]),
]


def premium_effect(i, L):
    """One short line for the message on an upgrade."""
    name, _b, _ic, _ab, _f, _vals, _what, rows = PREMIUM_DEF[i]
    return ", ".join(f"{values[L - 1]} {label.lower()}" for label, values in rows)


def premium_text(i, L):
    """An item of a rank: its effect with every rank side by side, this one in gold. Each rank is its own item type, so this needs no player's state."""
    _name, _b, _ic, _ab, _f, _vals, what, rows = PREMIUM_DEF[i]
    lines = [what] + [f"{label}: {TIPS._ranked(values, L)}" for label, values in rows]
    lines.append(f"{TIPS.GREEN}Max rank|r" if L == PREMIUM_LEVELS else f"{TIPS.ORANGE}Buy again for rank {L + 1}: {PREMIUM_PRICE} gold|r")
    return "|n".join(lines)


def premium_item_id(i, L):       # Lv 1 = the shop item Ip01..Ip08, higher levels Iu<i><L>
    return f"Ip0{i + 1}" if L == 1 else f"Iu{i + 1}{L}"


def premium_abil_id(i, L):
    return f"Xp0{i + 1}" if L == 1 else f"Xu{i + 1}{L}"


PREMIUM = [(premium_item_id(i, 1),) for i in range(len(PREMIUM_DEF))]
GLOVES_FAMILY = [d[0] for d in PREMIUM_DEF].index("Fury Gloves")   # shop list (Lv 1 ids)
PREMIUM_KEYS = "QWERASDF"

# Long Reach (Premium Armory, slot row 3): ONE buy = +REACH_STEP attack range, MELEE champions only (v2.1: the old
# 5 x +150 let ranged champions outrange the towers). Ranged buyers and a second buy are refunded. Applied instantly through a custom range upgrade (REACH_TECH,
# based on Long Rifles 'Rhri', effect 'ratr') that every hero lists under "upgrades used".
REACH_ITEM, REACH_TECH = "Ixr1", "Rcrg"
REACH_STEP, REACH_LEVELS, REACH_PRICE = 150, 1, 1500

# EPIC boss loot: every Nexus boss drops one crown, +all stats by level (lane bosses = Level 1, gate Levels 2-5).
#   (level, item id, ability id, name, all-stats bonus, icon)
EPIC_ITEMS = [
    (1, "Io01", "Xo01", "Champion's Crown", 200, "BTNHelmutPurple"),
    (2, "Io02", "Xo02", "Dark Crown", 400, "BTNHelmOfValor"),
    (3, "Io03", "Xo03", "Frozen Crown", 600, "BTNCirclet"),
    (4, "Io04", "Xo04", "Shadow Crown", 800, "BTNHoodOfCunning"),
    (5, "Io05", "Xo05", "Inferno Crown", 1000, "BTNHeartOfAszune"),
]

# Bank (secret grove): trade trees (lumber, +1 per cleared wave) for passive income.
BANK_ITEM = "Ib01"
INCOME_STEP = 100            # gold per minute per bought income (v3.5 Jiri: 1 tree -> +100 gold/min)
INCOME_TREE_COST = 1

SHOPS = {
    "armory": ("shpa", "Premium Armory", [p[0] for p in PREMIUM]),     # Long Reach not sold since v2.6 (no melee champion)
    "bank": ("shpc", "Bank", [BANK_ITEM]),
    "apothecary": ("shpb", "Apothecary", [f"Ipo{i}" for i in range(1, 5)] + ["bspd", "prvt", "rlif", "rwiz", "stel"]),
}
# The Apothecary sells potions as POWER-UP tokens (v3.4): a power-up is sold even to a FULL inventory (a normal item is
# refused - verified in-game), and the token adds one charge to the potion the champion carries (GivePotion), or puts a
# new potion into a free slot, or refunds when the inventory is full and holds no such potion.
POTION_TOKENS = [f"Ipo{i}" for i in range(1, 5)]          # one per POTIONS row, same order
POTION_ICONS = {"phea": "BTNPotionGreenSmall", "pman": "BTNPotionBlueSmall", "pres": "BTNPotionOfRestoration",
                "pnvl": "BTNLesserInvulneralbility"}
APOTHECARY_SLOTS = {"bspd": (0, 1), "prvt": (1, 1), "rlif": (2, 1), "rwiz": (3, 1), "stel": (0, 2)}   # tokens = row 1
# Apothecary potions (v1.7): heal a PERCENT of max HP / mana (the script does it on use - fixed amounts are useless
# for champions with thousands of HP), fixed price, and they STACK in the inventory (one slot, more charges).
#   (item, name, effect line, gold, hp %, mana %, native ability zeroed, its amount fields, cooldown s)
POTIONS = [
    ("phea", "Healing Potion", "Restores 50% HP", 100, 50, 0, "AIh1", [("Ihpg", 1)], 10.0),
    ("pman", "Mana Potion", "Restores 50% mana", 100, 0, 50, "AIm1", [("Impg", 1)], 10.0),
    ("pres", "Restoration Potion", "Restores all HP and mana", 250, 100, 100, "AIre", [("Ihps", 1), ("Imps", 2)], 30.0),
    ("pnvl", "Invulnerability Potion", "Invulnerable for a few seconds", 200, 0, 0, None, [], None),
]
SHOP_ITEMS = sorted({i for (_, _, items) in SHOPS.values() for i in items} - {p[0] for p in PREMIUM} - {BANK_ITEM, REACH_ITEM}
                    - set(POTION_TOKENS))   # originals only

CASTLE_ID = "hcd0"
# The castle is owned by Player 15 (neutral "extra" slot). Its shop gets BOTH buyer-selection abilities with a
# plaza-wide radius: a neutral-building one (like the grove shops) and an allied shop-sharing one.
CASTLE_SHOP_ABIL = "Xcsh"     # custom 'Aneu' (Neutral Building: select hero)
CASTLE_SHARE_ABIL = "Xcs2"    # custom 'Aall' (Shop Sharing, Allied Bldg.)
CIRCLE_ID = "ncd3"           # the player's coloured circle at his lane entrance = stat shop

# Stat shop at the lane circle (the player's own shop). Every item is instant and each buy costs PRICE_STEP_PCT % more:
# every price step is its own item type, the script swaps the stock when the item is picked up.
# Shop slots fill in order -> row 1 = Health Mana Damage Armor, row 2 = Strength Agility Intelligence All stats.
#   every kind is type "abil": the script adds the next copy of a hidden item-bonus ability to the hero
#   (copies with different ids stack). Attribute bonuses this way show as GREEN +N, not in the base value.
STAT_PER_LEVEL = 20     # single stats (Str / Agi / Int)  (v3.1, Jiri: was 10)
ALL_STATS_VALUE = 10    # the "All stats" buy           (v3.1, Jiri: was 3)
CB = "ReplaceableTextures\\CommandButtons\\"
STAT_ICON = {"str": CB + "BTNCDStr.blp", "agi": CB + "BTNCDAgi.blp", "int": CB + "BTNCDInt.blp"}   # imported (gen/icons.py)
# item-bonus ability fields (AbilityMetaData.slk): Iagi = data 1, Iint = data 2, Istr = data 3
KINDS_DEF = [
    {"item": "Ih", "name": "Health", "base": "AIlf", "fields": [("Ilif", 1)], "value": 600, "key": "Q", "icon": CB + "BTNHeal.blp", "abil": "Xh"},
    {"item": "Im", "name": "Mana", "base": "AImb", "fields": [("Iman", 1)], "value": 75, "key": "W", "icon": CB + "BTNBrilliance.blp", "abil": "Xm"},
    {"item": "Id", "name": "Damage", "base": "AIat", "fields": [("Iatt", 1)], "value": 20, "key": "E", "icon": CB + "BTNAttack.blp", "abil": "Xd"},
    {"item": "Ir", "name": "Armor", "base": "AId1", "fields": [("Idef", 1)], "value": 8, "key": "R", "icon": CB + "BTNDefend.blp", "abil": "Xa"},
    {"item": "Is", "name": "Strength", "base": "AIs1", "fields": [("Istr", 3)], "value": STAT_PER_LEVEL, "key": "A", "icon": STAT_ICON["str"], "abil": "Xs"},
    {"item": "Ia", "name": "Agility", "base": "AIa1", "fields": [("Iagi", 1)], "value": STAT_PER_LEVEL, "key": "S", "icon": STAT_ICON["agi"], "abil": "Xg"},
    {"item": "Ii", "name": "Intelligence", "base": "AIi1", "fields": [("Iint", 2)], "value": STAT_PER_LEVEL, "key": "D", "icon": STAT_ICON["int"], "abil": "Xi"},
    {"item": "Il", "name": "All stats", "base": "AIx1", "fields": [("Iagi", 1), ("Iint", 2), ("Istr", 3)], "value": ALL_STATS_VALUE, "key": "F", "icon": CB + "BTNStatUp.blp", "abil": "Xl"},
]
for _kd in KINDS_DEF:
    _kd["type"] = "abil"
# Experience (row 3, key Z): each buy = exactly one level's worth of XP for the champion (100 x (level + 1), the game's
# NeedHeroXP formula), so it stays worth one level at any level; price grows per buy like the stats.
KINDS_DEF.append({"item": "Ix", "name": "Experience", "type": "xp", "unam": "Experience +1 level", "value": 1,
                  "key": "Z", "icon": CB + "BTNTome.blp", "effect": "+1 level", "price": 250})
# Castle upgrades, sold by the CASTLE itself (allied shop, row 1 of its command card). One global price step
# per kind: the castle is shared and each castle bonus ability can only be added once.
#   castleheal: heals the castle by value; castleabil: adds the next copy of a hidden bonus ability to the castle
KINDS_DEF += [
    {"item": "Iy", "name": "Castle Health", "type": "castleabil", "base": "AIlf", "fields": [("Ilif", 1)], "value": 1000,
     "key": "Q", "slot": (0, 0), "icon": CB + "BTNCastle.blp", "abil": "Xy", "effect": "+1000 castle max HP"},
    {"item": "Ik", "name": "Castle Armor", "type": "castleabil", "base": "AId1", "fields": [("Idef", 1)], "value": 3,
     "key": "W", "slot": (1, 0), "icon": CB + "BTNStoneArchitecture.blp", "abil": "Xk", "effect": "+3 castle armor"},
    {"item": "Ie", "name": "Castle Regeneration", "type": "castleabil", "base": "Arel", "fields": [("Ihpr", 1)], "value": 10,
     "key": "E", "slot": (2, 0), "icon": CB + "BTNRegenerate.blp", "abil": "Xr", "effect": "+10 castle HP per second"},
    {"item": "Ic", "name": "Repair Castle", "type": "castleheal", "value": 2000, "repeat": True,
     "key": "R", "slot": (3, 0), "icon": CB + "BTNRepair.blp", "effect": "Heals the castle +2000 HP"},
    {"item": "Iw", "name": "Shockwave", "type": "castleshock", "value": 300, "repeat": True,
     "key": "A", "slot": (0, 1), "icon": CB + "BTNShockWave.blp", "effect": "Shockwave: 25% of their max HP to all wave monsters near the castle"},
]
CASTLE_TREE_COST = 1          # every castle upgrade costs 1 tree (lumber), no gold
CASTLE_SHOP_RANGE = 3400.0    # the whole plaza
CASTLE_OWN_REGEN = 5          # HP per second, the castle's own (OnTick: +10 every 2 s), on top of what was bought
KINDS = len(KINDS_DEF)
KIND_TYPE = {"abil": 1, "xp": 2, "castleheal": 3, "castleabil": 4, "castleshock": 5}
# Price steps per kind = item types + bonus abilities (copies stack only with distinct ids). 100 = the most the
# 2-digit ids allow; the script indexes gStatItem / gBonusAbil as kind * KIND_STRIDE + step.
STAT_TIERS, KIND_STRIDE = 100, 128
STAT_BASE_PRICE, STAT_PRICE_GROWTH = 100, 1.05     # v4.4, Jiri: +5 % per buy (+3 % since v3.1, before that +10 %)
PRICE_STEP_PCT = round((STAT_PRICE_GROWTH - 1) * 100)
assert STAT_TIERS <= 100 and STAT_TIERS <= KIND_STRIDE


def stat_item_id(s, k):
    return f"{KINDS_DEF[s]['item']}{k:02d}"


def bonus_abil_id(s, k):
    return f"{KINDS_DEF[s]['abil']}{k:02d}"


def kind_name(s):
    return KINDS_DEF[s]["name"]


def kind_value(s):
    return KINDS_DEF[s]["value"]


def stat_price(k, base=STAT_BASE_PRICE):
    return int(round(base * STAT_PRICE_GROWTH ** k))


def is_castle_kind(s):
    return KINDS_DEF[s]["type"].startswith("castle")


def kind_tiers(s):
    """Price steps / item types of kind s. Repeatable castle buys (repair, shockwave) are one item bought again and again."""
    return 1 if KINDS_DEF[s].get("repeat") else STAT_TIERS


def kind_slot(s):
    """Fixed button (x, y). Circle: rows 1-2 = the 8 stat kinds, row 3 = Experience. Castle shop: its own "slot"."""
    if is_castle_kind(s):
        return KINDS_DEF[s]["slot"]
    return (s % 4, s // 4)


def kind_title(s, k):
    """The name in the shop at step k (k buys so far). Lv = times bought; Castle Regeneration names what was bought (Jiri): a tier is its own item type."""
    kd = KINDS_DEF[s]
    if kd["item"] == "Ie":
        return f"{kd['name']}  |cff4fc3ff+{k * kd['value']} HP/s|r  (|cffffcc00{kd['key']}|r)"
    return f"{kd['name']}  |cff4fc3ffLv {k}|r  (|cffffcc00{kd['key']}|r)"


def kind_body(s, k):
    kd = KINDS_DEF[s]
    if kd["item"] == "Ie":
        return (f"Bought so far: +{k * kd['value']} HP/s. The castle's own +{CASTLE_OWN_REGEN} HP/s comes on top.|n"
                f"|cffff8c00Next buy: +{kd['value']} HP/s|r|n|cff80ff80Costs {CASTLE_TREE_COST} tree|r")
    if is_castle_kind(s):
        return f"{kind_effect(s)}|n|n|cff80ff80Costs {CASTLE_TREE_COST} tree|r"
    return f"{kind_effect(s)}|n|n|cffff8c00Next buy: +{PRICE_STEP_PCT}% gold|r"


def kind_effect(s):
    kd = KINDS_DEF[s]
    return kd.get("effect", f"+{kd['value']} {kd['name']}")
SOUL_ID = "ecd0"
BUYER_ID = "ecd1"


def base_id(d):
    return f"ns{d}0"


def turret_id(d):
    return f"nt{d}0"


def nexus_attack(dmg):
    """Attack fields for a Nexus building: one big chaos missile every NEXUS_COOLDOWN s at ground + air."""
    base, dice, sides = dmg
    return [("uaen", I, 1), ("ua1b", I, base), ("ua1d", I, dice), ("ua1s", I, sides), ("ua1c", U, NEXUS_COOLDOWN),
            ("ua1r", I, NEXUS_RANGE), ("uacq", U, float(NEXUS_RANGE + 50)), ("ua1t", S, "chaos"), ("ua1w", S, "missile"),
            ("ua1m", S, NEXUS_MISSILE), ("ua1z", I, 900), ("uma1", U, 0.15), ("ulpz", U, 200.0),
            ("ua1g", S, "ground,air,structure,debris,item,ward"), ("uwu1", I, 1)]


def wave_champion_id(d):     # weakened faction champion for waves (d 4-7: gate levels 2-5)
    return f"nc{d}0"


def boss_id(d, k):           # k = strength tier: 0 the Tower Warden (OnTowerDestroyed), 1 the Nexus boss (OnNexusDestroyed), 2 unused
    return f"nb{d}{k}"


BASE_HP, BASE_ARMOR = 15000, 10      # Jiri: v1.6 30000 -> 12000, v2.2 / 4 -> 3000, v3.9 x5 -> 15000
# Every Nexus fights back (huge attack, out of the tower's reach - see layout.tower_pos). v3.9: ~27 500 per shot, a bit
# more than its own tower (was 900 + 4d40, weaker than the tower)
NEXUS_DMG, NEXUS_COOLDOWN, NEXUS_RANGE = (27400, 4, 50), 2.5, 700
NEXUS_MISSILE = "Abilities\\Weapons\\FrostWyrmMissile\\FrostWyrmMissile.mdl"
TURRET_HP, TURRET_ARMOR, TURRET_DMG = 20000, 4, (24995, 1, 10)  # v3.9 (Jiri) HP x5, damage x10: ~25 000 chaos per hit / 1.3 s
# Towers and Nexuses are "Mechanical": WarCraft lifesteal does not work against mechanical targets.
NO_LIFESTEAL = [("utyp", S, "Mechanical")]
BOSS_HP = [35000, 60000, 90000]                               # v3.9 (Jiri): x10 (was 3500 / 6000 / 9000)
BOSS_ARMOR = [3, 4, 5]
# v4.3 (Jiri: bosses far too easy, ultra fast, high damage, durable, no stun). Lane and gate bosses grow with THEIR lane's wave when they rise, n = wave - 1:
# HP x (1 + BOSS_HP_GROWTH n^2), damage x (1 + BOSS_DMG_GROWTH n^2); their spells are their own, level 1 + wave / 5 + the gate's level (BOSS_SPELLS).
BOSS_HP_GROWTH, BOSS_DMG_GROWTH = 0.02, 0.008
BOSS_HP_FACTOR_MAX = 16.0                           # from about wave 28 the HP stops growing: the biggest boss, Level 5 with 8 players, has 39.7 million
BOSS_DMG_FACTOR_MAX = 8.0                           # from about wave 31 the attack stops growing: the Inferno boss hits for about 65 000; every bonus fits the bits
BOSS_COOLDOWN = 1.0
WARDEN_LEASH = 1500.0                               # a Tower Warden stays with its ruins, short of the Champion's Circle (1776 away)
# v4.4 (Jiri: bosses still far too easy, give them brutal real gear). Tier 0 the Tower Warden, tier 1 the Nexus boss. Real items in a real inventory, bound: nothing drops, nothing sells.
# Heart: a share of the base HP, so the wave and team factors count it too. No lifesteal, no regeneration, no invulnerability.
BOSS_GEAR = {"heart": (0.5, 1.0), "attack_speed": (0.5, 1.0), "crit_chance": (20.0, 25.0), "crit_times": 2.0, "armor": (25, 40), "spell_reduction": (0.20, 0.25)}
BOSS_SPEED = 522                                    # the engine's top speed; war3mapMisc.txt raises the map's cap from 400 for it
BOSS_SPELL_LEVELS = 10
BOSS_SPELL_DAMAGE = 1200.0                          # per spell level, what a single target takes
# base ability: our copy and how much of BOSS_SPELL_DAMAGE per field. Boss spells never touch a hero's copy of the same spell.
BOSS_SPELLS = {
    "ACfn": ("Xbfn", [("Ufn1", 1, 0.8), ("Ufn2", 2, 1.2)]),
    "ACbz": ("Xbbz", [("Hbz2", 2, 0.25), ("Hbz6", 6, 1.5)]),
    "Awrs": ("Xbws", [("Wrs1", 1, 1.0)]),
    "ACrf": ("Xbrf", [("Hbz2", 2, 0.25), ("Hbz6", 6, 1.5)]),
    "ACcv": ("Xbcv", [("Ucs1", 1, 1.0), ("Ucs2", 2, 20.0)]),
    "ACsh": ("Xbsh", [("Osh1", 1, 1.0), ("Osh2", 2, 20.0)]),
    "ACtc": ("Xbtc", [("Ctc1", 1, 1.0)]),
}


def boss_abils(abils):
    """A boss's ability list with its own spell copies, and the inventory its gear sits in."""
    return ",".join(BOSS_SPELLS[a][0] if a in BOSS_SPELLS else a for a in abils.split(",")) + ",AInv"


def gear_heart_id(li, tier):       # li 0 a personal lane, 1-4 gate levels 2-5
    return f"Jh{li}{tier}"


def gear_hands_id(tier):
    return f"Jg0{tier}"


def gear_plate_id(tier):
    return f"Jp0{tier}"


def boss_base_hp(li, tier):
    return BOSS_HP[tier] * (GATE_LEVELS[li - 1]["boss"][2] if li else 1)


def gear_heart_bonus(li, tier):
    return int(boss_base_hp(li, tier) * BOSS_GEAR["heart"][tier])


def boss_gear_abilities():
    out = []
    for tier in (0, 1):
        for li in range(1 + len(GATE_LEVELS)):
            out.append(("AIlf", f"Yh{li}{tier}", [("Ilif", I, 1, 1, gear_heart_bonus(li, tier))]))
        out.append(("AIsx", f"Ys0{tier}", [("Isx1", U, 1, 1, BOSS_GEAR["attack_speed"][tier])]))
        out.append(("AIcs", f"Yc0{tier}", [("Ocr1", U, 1, 1, BOSS_GEAR["crit_chance"][tier]), ("Ocr2", U, 1, 2, BOSS_GEAR["crit_times"]), ("Ocr3", U, 1, 3, 0.0), ("Ocr4", U, 1, 4, 0.0)]))
        out.append(("AId5", f"Ya0{tier}", [("Idef", I, 1, 1, BOSS_GEAR["armor"][tier])]))
        out.append(("AIsr", f"Yr0{tier}", [("isr2", U, 1, 2, BOSS_GEAR["spell_reduction"][tier])]))
    return out


def _bound_gear(base, uid, name, icon, text, abilities):
    bound = [("idro", I, 0), ("idrp", I, 0), ("ipaw", I, 0), ("isel", I, 0), ("iusa", I, 0), ("iper", I, 0), ("ipow", I, 0), ("igol", I, 0), ("ilum", I, 0), ("ilev", I, 10)]
    return (base, uid, [("unam", S, name), ("iico", S, CB + icon + ".blp"), ("utip", S, f"|cffff4040{name}|r"), ("utub", S, text), ("ides", S, text), ("iabi", S, abilities)] + bound)


def boss_gear_items():
    out = []
    for tier in (0, 1):
        for li in range(1 + len(GATE_LEVELS)):
            out.append(_bound_gear("rlif", gear_heart_id(li, tier), "Heart of Ruin", "BTNHeartOfAszune", f"+{gear_heart_bonus(li, tier)} HP, before its wave's growth.|nBound: it does not drop.", f"Yh{li}{tier}"))
        speed, chance = round(BOSS_GEAR["attack_speed"][tier] * 100), round(BOSS_GEAR["crit_chance"][tier])
        out.append(_bound_gear("ratc", gear_hands_id(tier), "Executioner Gauntlets", "BTNGauntletsOfOgrePower", f"+{speed}% attack speed, {chance}% chance of {round(BOSS_GEAR['crit_times'])}x damage.|nBound: it does not drop.", f"Ys0{tier},Yc0{tier}"))
        armor, reduction = BOSS_GEAR["armor"][tier], round(BOSS_GEAR["spell_reduction"][tier] * 100)
        out.append(_bound_gear("rde4", gear_plate_id(tier), "Runic Warplate", "BTNHumanArmorUpThree", f"+{armor} armor, {reduction}% less spell damage.|nBound: it does not drop.", f"Ya0{tier},Yr0{tier}"))
    return out


def boss_spell_ids(abils):
    """The ids of cast 1 and cast 2: the first two abilities of the list."""
    first, second = abils.split(",")[:2]
    return BOSS_SPELLS[first][0], BOSS_SPELLS[second][0]


def boss_spell_abilities():
    out = []
    meta = _ref_slk("Units_AbilityMetaData.slk")
    data = _ref_slk("Units_AbilityData.slk")
    common = {"atar": "targs", "aare": "Area", "aran": "Rng", "acas": "Cast", "adur": "Dur", "ahdu": "HeroDur", "abuf": "BuffID", "aeff": "EfctID"}
    for base, (aid, fields) in BOSS_SPELLS.items():
        row = data[base]
        ours = {f for (f, _p, _s) in fields}
        mods = [("alev", I, 0, 0, BOSS_SPELL_LEVELS)]
        specific = {f: m for f, m in meta.items() if m.get("field") == "Data" and base in (m.get("useSpecific") or "").split(",") and f not in ours}
        for level in range(1, BOSS_SPELL_LEVELS + 1):
            # the native's own cooldown at every level: without it the engine's own use of a creep spell has no limit
            mods += [("amcs", I, level, 0, 0), ("acdn", U, level, 0, float(row["Cool1"]))]
            mods += [(field, U, level, pointer, BOSS_SPELL_DAMAGE * share * level) for (field, pointer, share) in fields]
            # a new level has nothing of level 1 unless it is written: range, area, targets, waves, buffs
            for field, column in common.items():
                value = row.get(f"{column}1", "")
                if value in ("", "-", "_", None):
                    continue
                kind = S if field in ("atar", "abuf", "aeff") else U
                mods.append((field, kind, level, 0, value if kind == S else float(value)))
            for field, m in specific.items():
                value = row.get("Data" + "ABCDEFGHI"[int(m["data"]) - 1] + "1", "")
                if value in ("", "-", "_", None):
                    continue
                if m.get("type") == "int":
                    mods.append((field, I, level, int(m["data"]), int(float(value))))
                elif m.get("type") in ("unreal", "real"):
                    mods.append((field, U if m.get("type") == "unreal" else R, level, int(m["data"]), float(value)))
        out.append((base, aid, mods))
    return out
BOSS_DMG = [(1400, 2, 400), (1900, 2, 500), (2400, 2, 600)]       # v3.9 (Jiri): x50 (was 28+2d8, 38+2d10, 48+2d12)


def _avg(dmg):
    base, dice, sides = dmg
    return base + dice * (sides + 1) / 2


def building_ladder():
    """[(name, average damage per hit)] in progression order: Level 1 tower, Level 1 Nexus, Level 2 tower, ... Level 5 Nexus."""
    out = [("Level 1 tower", _avg(TURRET_DMG)), ("Level 1 Nexus", _avg(NEXUS_DMG))]
    for g in GATE_LEVELS:
        out += [(f"Level {g['level']} tower", _avg(g["tower"][2])), (f"Level {g['level']} Nexus", _avg(g["nexus"][2]))]
    return out


_ladder = building_ladder()
assert all(a[1] < b[1] for a, b in zip(_ladder, _ladder[1:])), f"every next building must hit harder: {_ladder}"
assert all(GATE_LEVELS[i]["tower"][0] < GATE_LEVELS[i + 1]["tower"][0] and GATE_LEVELS[i]["nexus"][0] < GATE_LEVELS[i + 1]["nexus"][0]
           for i in range(len(GATE_LEVELS) - 1)) and TURRET_HP < GATE_LEVELS[0]["tower"][0] and BASE_HP < GATE_LEVELS[0]["nexus"][0], \
    "every next level's tower and Nexus must have more HP"


# ---- The FINAL BOSS (v4.0, Jiri: "ultra strong, stats based on the minute, immune to stuns, his own stun skills").
# He rises when every lane boss and all 4 gate levels are done; his death wins the game (StartFinalBoss, castle_logic.j).
# Stats follow the game clock, minute m - at spawn and on every new minute of the fight (FinalApplyStats):
#   max HP = (FINAL_HP_BASE + FINAL_HP_PER_MIN * m) * player factor (1-2 / 3-5 / 6-8 players: 1 / 2 / 3)
#   damage = FINAL_DMG_BASE + FINAL_DMG_PER_MIN * m;  armor = FINAL_ARMOR_BASE + m / FINAL_ARMOR_EVERY
# 1.27 can't set max HP / damage / armor directly: "bit" abilities (distinct ids stack, FinalBits) add any amount.
# Spells: FINAL_TIERS copies of each with stronger damage, one tier up every FINAL_TIER_EVERY minutes.
FINAL_BOSS_ID = "nbf0"
FINAL_BOSS_NAME = "Kharazul the World Ender"
FINAL_HP_UNIT, FINAL_HP_BASE, FINAL_HP_PER_MIN = 1000000, 5000000, 250000
FINAL_DMG_BASE, FINAL_DMG_PER_MIN = 20000, 1000
FINAL_ARMOR_BASE, FINAL_ARMOR_EVERY = 30, 2
FINAL_REGEN = 500.0
FINAL_HP_BITS, FINAL_HP_STEP = 10, 100000       # +100 000 .. +51 200 000
FINAL_DMG_BITS, FINAL_DMG_STEP = 10, 100        # +100 .. +51 200
FINAL_ARMOR_BITS = 7                            # +1 .. +64
FINAL_TIERS, FINAL_TIER_EVERY = 10, 5
FINAL_SPELL_PREFIX = ["Xfb", "Xfs", "Xfw", "Xfi"]      # Storm Bolt, War Stomp, Shockwave, Inferno (order: FinalBossTick)
FINAL_BASH = "Xfbh"


def final_bit_ids():
    """gFinalBit: HP bits, then damage bits, then armor bits."""
    return [f"Xfh{i}" for i in range(FINAL_HP_BITS)] + [f"Xfd{i}" for i in range(FINAL_DMG_BITS)] + [f"Xfa{i}" for i in range(FINAL_ARMOR_BITS)]


def final_boss_abilities():
    out = []
    for i in range(FINAL_HP_BITS):
        out.append(("AIlf", f"Xfh{i}", [("Ilif", I, 1, 1, FINAL_HP_STEP << i)]))
    for i in range(FINAL_DMG_BITS):
        out.append(("AIat", f"Xfd{i}", [("Iatt", I, 1, 1, FINAL_DMG_STEP << i)]))
    for i in range(FINAL_ARMOR_BITS):
        out.append(("AId1", f"Xfa{i}", [("Idef", I, 1, 1, 1 << i)]))
    free = [("amcs", I, 1, 0, 0)]
    for t in range(FINAL_TIERS):
        k = float(t + 1)
        out.append(("ACtb", f"Xfb{t}", free + [("Ctb1", U, 1, 1, 4000.0 * k), ("aran", U, 1, 0, 1000.0), ("acdn", U, 1, 0, 4.0),
                                               ("adur", U, 1, 0, 2.5), ("ahdu", U, 1, 0, 2.5)]))
        out.append(("Awrs", f"Xfs{t}", free + [("Wrs1", U, 1, 1, 3000.0 * k), ("aare", U, 1, 0, 450.0), ("acdn", U, 1, 0, 5.0),
                                               ("adur", U, 1, 0, 2.0), ("ahdu", U, 1, 0, 2.0)]))
        out.append(("ACsh", f"Xfw{t}", free + [("Osh1", U, 1, 1, 4000.0 * k), ("Osh2", U, 1, 2, 9999999.0), ("Osh3", U, 1, 3, 1200.0),
                                               ("aran", U, 1, 0, 1000.0), ("acdn", U, 1, 0, 8.0)]))
        out.append(("ANin", f"Xfi{t}", free + [("aher", I, 0, 0, 0), ("Uin1", U, 1, 1, 5000.0 * k), ("Uin2", U, 1, 2, 30.0), ("aare", U, 1, 0, 300.0),
                                               ("aran", U, 1, 0, 1000.0), ("acdn", U, 1, 0, 15.0), ("adur", U, 1, 0, 2.0), ("ahdu", U, 1, 0, 2.0)]))
    out.append(("ACbh", FINAL_BASH, [("Hbh1", U, 1, 1, 25.0), ("Hbh3", U, 1, 3, 0.0), ("adur", U, 1, 0, 1.0), ("ahdu", U, 1, 0, 1.0)]))
    return out


def final_boss_unit():
    return ("nbal", FINAL_BOSS_ID, [
        ("unam", S, FINAL_BOSS_NAME), ("uhpm", I, FINAL_HP_UNIT), ("udef", I, FINAL_ARMOR_BASE), ("udty", S, "hero"),
        ("uhpr", U, FINAL_REGEN), ("uhrt", S, "always"), ("umpm", I, 1000), ("umpi", I, 1000), ("umpr", U, 10.0),
        ("ua1b", I, FINAL_DMG_BASE - 1), ("ua1d", I, 1), ("ua1s", I, 1), ("ua1c", U, 1.2), ("ua1r", I, 700), ("uacq", U, 900.0),
        ("ua1t", S, "chaos"), ("ua1w", S, "missile"), ("ua1m", S, "Abilities\\Weapons\\DemonHunterMissile\\DemonHunterMissile.mdl"),
        ("ua1z", I, 1200), ("ua1g", S, "ground,air,structure,debris,item,ward"), ("uabi", S, FINAL_BASH),
        ("umdl", S, "units\\demon\\Warlock\\Warlock.mdl"), ("uico", S, CB + "BTNArchimonde.blp"), ("usnd", S, "Warlock"),
        ("usca", R, 2.4), ("ussc", R, 4.0), ("ucol", U, 64.0), ("umvs", I, 320), ("ulev", I, 20), ("usid", I, 1200), ("usin", I, 1200),
        ("ubba", I, 5000), ("ubdi", I, 1), ("ubsi", I, 1)])


def custom_units():
    units = []
    no_bounty = [("ubba", I, 0), ("ubdi", I, 0), ("ubsi", I, 0)]
    units.append(final_boss_unit())
    units.append(("hcas", CASTLE_ID, [
        ("unam", S, "Castle of Lordaeron"), ("uhpm", I, 8000), ("udef", I, 10),
        # allied shop: players buy the castle upgrades here (CASTLE_SHOP_ABIL = Aall with a plaza-wide radius)
        ("uabi", S, f"{CASTLE_SHOP_ABIL},{CASTLE_SHARE_ABIL},Apit,Asid"), ("utra", S, ""), ("ures", S, ""), ("uupt", S, ""),
        ("usid", I, 1400), ("usin", I, 1400)] + no_bounty))
    # Invisible "buyer": taverns only sell to a unit of the player standing nearby, so every player
    # gets this hidden helper in the middle of the hall. Practically invisible (scale 0.01, no shadow,
    # not on the minimap, not a worker -> no idle-worker icon, cannot move); the hall is pre-selected
    # for the player, so nobody ever sees or touches it. Removed as soon as the champion is picked.
    units.append(("ewsp", SOUL_ID, [
        ("unam", S, "Champion Select"), ("uabi", S, "Avul"), ("ubui", S, ""), ("ufoo", I, 0),
        ("usca", R, 0.01), ("ussc", R, 0.01), ("ushu", S, ""), ("uhom", I, 1), ("utyp", S, ""),
        ("umvs", I, 0), ("usid", I, 0), ("usin", I, 0)] + no_bounty))
    # A dead champion's buyer: shops sell only to a nearby living unit with an inventory. It stands in the dark while he is dead (BuyerTick). Hidden or with Locust the game does not take it as a patron.
    units.append(("ewsp", BUYER_ID, [
        ("unam", S, "Champion's Buyer"), ("uabi", S, "AInv,Avul"), ("ubui", S, ""), ("ufoo", I, 0),
        ("usca", R, 0.01), ("ussc", R, 0.01), ("ushu", S, ""), ("uhom", I, 1), ("utyp", S, ""),
        ("umvs", I, 0), ("usid", I, 0), ("usin", I, 0)] + no_bounty))
    units.append(("ncp3", CIRCLE_ID, [
        ("unam", S, "Champion's Circle"), ("uabi", S, "Avul,Aall,Apit,Asid"), ("usei", S, ""),
        ("utip", S, "Champion's Circle"),
        ("utub", S, f"Your lane. Buy stats for your champion here - instant; every buy costs {PRICE_STEP_PCT}% more.")]))
    for (tid, name, heroes) in TAVERNS:
        units.append(("ntav", tid, [("unam", S, name), ("useu", S, ",".join(heroes))]))
    units += xhs_custom_units()
    for (sid, name, items) in SHOPS.values():
        mods = [("unam", S, name), ("usei", S, ",".join(items))]
        if sid == SHOPS["bank"][0]:      # looks like a gold mine
            mods += [("umdl", S, "Buildings\\Other\\GoldMine\\GoldMine.mdl"), ("uico", S, CB + "BTNGoldMine.blp")]
        units.append(("ngme", sid, mods))
    for d, f in enumerate(FACTIONS):
        bb, bname = f["base"]
        tb, tname = f["turret"]
        b = f["boss"]
        units.append((bb, base_id(d), [
            ("unam", S, bname), ("uhpm", I, BASE_HP), ("udef", I, BASE_ARMOR), ("udty", S, "fort"),
            ("uabi", S, ""), ("utra", S, ""), ("ures", S, ""), ("uupt", S, "")] + nexus_attack(NEXUS_DMG) + NO_LIFESTEAL + [
            ("usid", I, 1000), ("usin", I, 1000), ("ubba", I, 200), ("ubdi", I, 1), ("ubsi", I, 1)]))
        base, dice, sides = TURRET_DMG
        units.append((tb, turret_id(d), [
            ("unam", S, tname), ("uhpm", I, TURRET_HP), ("udef", I, TURRET_ARMOR), ("udty", S, "fort"),
            ("ua1b", I, base), ("ua1d", I, dice), ("ua1s", I, sides), ("ua1c", U, 1.3),
            ("ua1r", I, 750), ("uacq", U, 800.0), ("ua1t", S, "chaos"), ("uabi", S, "")] + NO_LIFESTEAL + [
            ("usid", I, 1000), ("usin", I, 1000), ("usca", R, 1.25),
            ("ubba", I, 100), ("ubdi", I, 1), ("ubsi", I, 1)]))
        for k in range(3):
            base, dice, sides = BOSS_DMG[k]
            mods = [
                ("unam", S, f"{tname} Warden" if k == 0 else b["name"]), ("uhpm", I, BOSS_HP[k]), ("udef", I, BOSS_ARMOR[k]),
                ("udty", S, "hero"), ("uhpr", U, 2.0), ("uhrt", S, "always"),
                ("umpm", I, 1000), ("umpi", I, 1000), ("umpr", U, 4.0),
                ("ua1b", I, base), ("ua1d", I, dice), ("ua1s", I, sides), ("ua1c", U, BOSS_COOLDOWN),
                ("ua1r", I, b["range"]), ("uacq", U, 900.0), ("ua1t", S, "chaos"),
                ("uabi", S, boss_abils(b["abils"])), ("usca", R, b["scale"]), ("ussc", R, 3.0),
                ("ucol", U, 40.0), ("umvs", I, BOSS_SPEED), ("ulev", I, 10), ("usid", I, 1000), ("usin", I, 1000),
                ("ubba", I, 150 if k == 0 else 300), ("ubdi", I, 1), ("ubsi", I, 1),
            ]
            for key, fid in (("model", "umdl"), ("icon", "uico"), ("missile", "ua1m"), ("sound", "usnd")):
                if key in b:
                    mods.append((fid, S, b[key]))
            units.append((b["base"], boss_id(d, k), mods))
    # gate levels: tower + Nexus + boss per level
    for g in GATE_LEVELS:
        arm, (tr, tg, tb) = g["arm"], g["tint"]
        nhp, narm, ndmg = g["nexus"]
        units.append((g["base"][0], base_id(arm), [
            ("unam", S, g["base"][1]), ("uhpm", I, nhp), ("udef", I, narm),
            ("udty", S, "fort"), ("uabi", S, ""), ("utra", S, ""), ("ures", S, ""), ("uupt", S, "")] + nexus_attack(ndmg) + NO_LIFESTEAL + [
            ("usid", I, 1000), ("usin", I, 1000), ("ubba", I, g["gold"]), ("ubdi", I, 1), ("ubsi", I, 1),
            ("usca", R, g["nexus_scale"]), ("uclr", I, tr), ("uclg", I, tg), ("uclb", I, tb)]))
        thp, tarm, (sb, sd, ss) = g["tower"]
        units.append((g["turret"][0], turret_id(arm), [
            ("unam", S, g["turret"][1]), ("uhpm", I, thp), ("udef", I, tarm),
            ("udty", S, "fort"), ("ua1b", I, sb), ("ua1d", I, sd), ("ua1s", I, ss), ("ua1c", U, 1.3),
            ("ua1r", I, 800), ("uacq", U, 850.0), ("ua1t", S, "chaos"), ("uabi", S, ""), ("uaen", I, 1)] + NO_LIFESTEAL + [
            ("usid", I, 1000), ("usin", I, 1000), ("usca", R, g["tower_scale"]), ("uclr", I, tr), ("uclg", I, tg), ("uclb", I, tb),
            ("ubba", I, g["gold"] // 2), ("ubdi", I, 1), ("ubsi", I, 1)]))
        src, bname, hpm, dmgm, bscale = g["boss"]
        b = FACTIONS[src]["boss"]
        for k in (0, 1):
            base, dice, sides = BOSS_DMG[k]
            mods = [
                ("unam", S, f"{g['turret'][1]} Warden" if k == 0 else bname), ("uhpm", I, BOSS_HP[k] * hpm), ("udef", I, BOSS_ARMOR[k] + 2 * g["level"]),
                ("udty", S, "hero"), ("uhpr", U, 2.0 * hpm), ("uhrt", S, "always"),
                ("umpm", I, 2000), ("umpi", I, 2000), ("umpr", U, 8.0),
                ("ua1b", I, int(base * dmgm)), ("ua1d", I, dice), ("ua1s", I, sides), ("ua1c", U, BOSS_COOLDOWN),
                ("ua1r", I, b["range"]), ("uacq", U, 900.0), ("ua1t", S, "chaos"),
                ("uabi", S, boss_abils(b["abils"])), ("usca", R, bscale), ("ussc", R, 3.0),
                ("ucol", U, 40.0), ("umvs", I, BOSS_SPEED), ("ulev", I, 10 + g["level"]), ("usid", I, 1000), ("usin", I, 1000),
                ("ubba", I, g["gold"] // 2 if k == 0 else g["gold"]), ("ubdi", I, 1), ("ubsi", I, 1),
                ("uclr", I, tr), ("uclg", I, tg), ("uclb", I, tb)]
            for key, fid in (("model", "umdl"), ("icon", "uico"), ("missile", "ua1m"), ("sound", "usnd")):
                if key in b:
                    mods.append((fid, S, b[key]))
            units.append((b["base"], boss_id(arm, k), mods))
    # standardized wave units (q<arm><stage><m|r>)
    for arm, f in enumerate(FACTIONS + GATE_LEVELS):
        for st, pair in enumerate(f["stages"]):
            for ranged, model_unit in enumerate(pair):
                hp, dmg = (WAVE_RANGED_HP, WAVE_RANGED_DMG) if ranged else (WAVE_MELEE_HP, WAVE_MELEE_DMG)
                units.append((model_unit, wave_unit_id(arm, st, ranged), [
                    ("uhpm", I, int(hp * WAVE_STAGE_HP[st])), ("ua1b", I, int(dmg * WAVE_STAGE_DMG[st]) - 1), ("ua1d", I, 1), ("ua1s", I, 1),
                    ("ua1c", U, WAVE_RANGED_COOLDOWN if ranged else WAVE_MELEE_COOLDOWN),
                    ("ua1w", S, "missile" if ranged else "normal"), ("ua1r", I, WAVE_RANGED_RANGE if ranged else WAVE_MELEE_RANGE),
                    ("udef", I, WAVE_RANGED_ARMOR if ranged else WAVE_MELEE_ARMOR)] + WAVE_SAME + NO_BOUNTY))
    # weakened wave champions (every 10th wave): half damage, about half HP, smaller model
    for d, f in enumerate(FACTIONS + GATE_LEVELS):
        units.append((f["champion"], wave_champion_id(d), [
            ("uhpm", I, WAVE_CHAMP_HP), ("udef", I, WAVE_CHAMP_ARMOR), ("ua1b", I, WAVE_CHAMP_DMG[0]),
            ("ua1d", I, WAVE_CHAMP_DMG[1]), ("ua1s", I, WAVE_CHAMP_DMG[2]), ("usca", R, WAVE_CHAMP_SCALE),
            ("ua1c", U, WAVE_MELEE_COOLDOWN), ("ua1w", S, "normal"), ("ua1r", I, WAVE_MELEE_RANGE)] + WAVE_SAME + NO_BOUNTY))
    return units


# Hero levels: practically unlimited (MAX_HERO_LEVEL in war3mapMisc.txt). A hero's five skills are all learnable by level 20; past that every
# level-up adds ATTR_PER_LEVEL to Str/Agi/Int by itself. (A sixth "Attributes" skill does not fit: a hero ability list holds at most 5.)
MAX_HERO_LEVEL = 1000
ATTR_PER_LEVEL = 30           # Jiri (v3.5): +30 Str/Agi/Int
ATTR_AUTO_ABOVE = 20


def hero_base_armor(hero_id):
    """Base armor of a hero in the game's data (Units\\UnitBalance.slk `def`; a custom hero copies its base unit)."""
    base = XHS.UNITS[hero_id][0]
    return float(_ref_slk("Units_UnitBalance.slk")[base]["def"]) - 2.0     # MiscGame AgiDefenseBase = -2


def _ref_slk(name):
    import os
    from slk import read_slk
    cache = globals().setdefault("_REF_CACHE", {})
    if name not in cache:
        cache[name] = read_slk(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ref", name))
    return cache[name]


def _no_level(mods):
    return [(f, k, v) for (f, k, _l, _p, v) in mods]


# Natives our own bosses and final boss also use (Awrs, ACce): the champions' edited copies get ids of their own, so nothing else changes.
XHS_REMAP = {"ACce": "Xhce", "Awrs": "Xhws"}


def _remap_list(value):
    return ",".join(XHS_REMAP.get(a, a) for a in value.split(","))


def _xhs_unit_mods(uid, base, mods):
    """A unit's mods from the reference, with its ability list naming our copies. A list it only inherits gets written out when it names one."""
    plain = _no_level(mods)
    if any(m[0] == "uabi" for m in plain):
        return [(f, k, _remap_list(v)) if f == "uabi" else (f, k, v) for (f, k, v) in plain]
    inherited = _ref_slk("Units_UnitAbilities.slk").get(base, {}).get("abilList", "")
    if any(a in XHS_REMAP for a in inherited.split(",")):
        return plain + [("uabi", S, _remap_list(inherited))]
    return plain


def hero_tavern_mods(h):
    """A tavern hero: free, 12 fixed buttons, one hotkey each, short tooltip."""
    i = ALL_HEROES.index(h)
    x, y = i % 4, i // 4
    name = next((v for (f, _k, _l, _p, v) in XHS.UNITS[h][2] if f == "unam"), None) or _ref_profile_name(h)
    key = TAVERN_KEYS[i]
    skills = ", ".join(f"|cffffcc00{SKILL_KEYS[k]}|r {XHS_SKILLS[a][0]}" for k, a in enumerate(HERO_SKILLS[h]))
    # (a standard hero needs a Keep and a Castle for a second purchase: tiers of a base-building game. This map builds nothing, and a second round is a first hero again.)
    return [("ugol", I, 0), ("ulum", I, 0), ("ufoo", I, 0), ("usst", I, 0), ("usma", I, 8), ("usrg", I, 1), ("ureq", S, ""),
            ("urqc", I, 0), ("urq1", S, ""), ("urq2", S, ""),
            ("ubpx", I, x), ("ubpy", I, y), ("uhot", S, key),
            ("uhab", S, ",".join(HERO_SKILLS[h])),
            ("utip", S, f"|cffffcc00{name}|r  (|cffffcc00{key}|r)"),
            ("utub", S, f"{XHS_TIPS[h]}|n{skills}.|n|cff4fc3ffHero level 20:|r {_level20_names(h)}")]


def _ref_profile_name(h):
    import glob
    import os
    from slk import read_profile
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ref")
    for path in glob.glob(os.path.join(root, "Units_*UnitStrings.txt")):
        section = read_profile(path).get(h)
        if section and section.get("Name"):
            return section["Name"].strip('"')
    raise SystemExit(f"no name for hero {h}")


def xhs_custom_units():
    """The Dryad (a custom hero in the reference too) and the custom summons."""
    out = []
    for uid, (base, custom, mods) in XHS.UNITS.items():
        if custom:
            plain = [m for m in _xhs_unit_mods(uid, base, mods) if not (uid in HERO_SKILLS and m[0] == "uhab")]
            out.append((base, uid, plain + (hero_tavern_mods(uid) if uid in HERO_SKILLS else [])))
    return out


def original_unit_mods():
    """The standard heroes and summons, edited as in the reference; the heroes also sold in our tavern."""
    out = []
    for uid, (base, custom, mods) in XHS.UNITS.items():
        if custom:
            continue
        plain = _xhs_unit_mods(uid, base, mods)
        if uid in HERO_SKILLS:
            plain = [m for m in plain if m[0] != "uhab"] + hero_tavern_mods(uid)
        elif uid == "Edmm":      # his demon form has the same five skills, in the same order
            plain = [m for m in plain if m[0] != "uhab"] + [("uhab", S, ",".join(HERO_SKILLS["Edem"]))]
        out.append((uid, plain))
    return out


def _ability_levels(aid, base):
    for (f, _k, _l, _p, v) in XHS.ABILS[aid][2] if aid in XHS.ABILS else ():
        if f == "alev":
            return int(v)
    return int(_ref_slk("Units_AbilityData.slk")[base]["levels"])


def _card_mods(aid, key, pos, learn_pos):
    """The hotkey and the button of an ability, cast and switch-off state alike (Immolation, autocast); learn_pos only for learnable skills."""
    x, y = pos
    mods = [("ahky", S, 0, 0, key), ("auhk", S, 0, 0, key), ("abpx", I, 0, 0, x), ("abpy", I, 0, 0, y), ("aubx", I, 0, 0, x), ("auby", I, 0, 0, y)]
    if learn_pos:
        mods += [("arhk", S, 0, 0, key), ("arpx", I, 0, 0, learn_pos[0]), ("arpy", I, 0, 0, learn_pos[1])]
    return mods


def _level20_names(h):
    """What a champion gets at hero level 20, the way his innate ability names it: he cannot see it on his card before."""
    grants = [a for a in XHS.LEVEL20[h][0] if a != "A03Q"]
    return ", ".join(f"{XHS_SKILLS[a][0]} [{GRANT_KEY}]" for a in grants) + (", a stronger Battle Roar" if "A03Q" in XHS.LEVEL20[h][0] else "")


def _text_mods(aid, key, learnable, grant=False, preview=""):
    data = LEARN_ORIGIN.get(aid, aid)
    return [(field, S, level, 0, text) for (field, level, text) in TIPS.ability_tips(data, XHS_SKILLS[aid][0], key, learnable, grant, preview)]


def xhs_ability_mods():
    """{ability id: our mods}: the card every champion has, the same as the reference's. Q W E R on the bottom row, T beside the innate
    ability (D), and the level 20 ability (F) where the Learn button is once every skill is learned."""
    ours = {}
    for h, skills in HERO_SKILLS.items():
        for slot, aid in enumerate(skills):
            pos = (slot, 2) if slot < 4 else (2, 1)
            learn = (slot, 0) if slot < 4 else (0, 1)
            ours[aid] = _card_mods(aid, SKILL_KEYS[slot], pos, learn) + _text_mods(aid, SKILL_KEYS[slot], True)
        uabi = next((v for (f, _k, _l, _p, v) in XHS.UNITS[h][2] if f == "uabi"), "")
        for aid in [a for a in uabi.split(",") if a and a != "AInv"]:
            ours[aid] = _card_mods(aid, INNATE_KEY, (1, 1), None) + _text_mods(aid, INNATE_KEY, False, preview=f"At hero level 20: {_level20_names(h)}")
        for aid in XHS.LEVEL20[h][0]:
            key, pos = (INNATE_KEY, (1, 1)) if aid == "A03Q" else (GRANT_KEY, (3, 1))      # the Tauren's new roar replaces his old one
            ours[aid] = _card_mods(aid, key, pos, None) + _text_mods(aid, key, False, grant=True)
    # War Drums is a placeholder to learn: each rank swaps in a real aura of its own, which must read like that rank
    for rank, aid in enumerate(("A033", "A046", "A047", "A048"), start=1):
        ours[aid] = _card_mods(aid, SKILL_KEYS[4], (2, 1), None) + [(f, S, lvl, 0, text) for (f, lvl, text) in TIPS.drum_tips(rank, SKILL_KEYS[4])]
    return ours


def tooltip_texts():
    """Every ability text of the champions, for the build's check: the engine crashes on one that is too long."""
    return [(aid, f"{field} rank {lvl}", field, value) for aid, mods in xhs_ability_mods().items() for (field, _k, lvl, _p, value) in mods if field in ("atp1", "aub1", "aut1", "auu1", "aret", "arut")]


LAYOUT_FIELDS = {"ahky", "auhk", "arhk", "abpx", "abpy", "aubx", "auby", "arpx", "arpy"}


def _with_ours(aid, mods, ours):
    """The reference's mods, its layout replaced by ours where we set one."""
    if aid not in ours:
        return list(mods)
    return [m for m in mods if m[0] not in LAYOUT_FIELDS] + ours[aid]


def xhs_original_abilities():
    ours = xhs_ability_mods()
    out = [(aid, _with_ours(aid, mods, ours)) for aid, (_b, custom, mods) in XHS.ABILS.items() if not custom and aid not in XHS_REMAP and aid not in LEARN_REMAP]
    done = {a for a, _m in out}
    # a skill the reference left as it is (no mods) still gets our card and text
    return out + [(aid, mods) for aid, mods in ours.items() if aid not in done and aid not in XHS.ABILS and aid not in LEARN_ORIGIN]


def xhs_custom_abilities():
    ours = xhs_ability_mods()
    out = [(base, aid, _with_ours(aid, mods, ours)) for aid, (base, custom, mods) in XHS.ABILS.items() if custom]
    out += [(old, new, _with_ours(new, XHS.ABILS[old][2], ours)) for old, new in LEARN_REMAP.items()]
    return out + [(aid, new, XHS.ABILS[aid][2]) for aid, new in XHS_REMAP.items()]


def custom_buffs():
    """war3map.w3h: (custom, originals) as the reference has them, with art and no text."""
    custom = [(base, bid, _no_level(mods)) for bid, (base, is_custom, mods) in XHS.BUFFS.items() if is_custom]
    originals = [(bid, _no_level(mods)) for bid, (_b, is_custom, mods) in XHS.BUFFS.items() if not is_custom]
    return custom, originals


def custom_upgrades():
    """war3map.w3q: Long Reach = +REACH_STEP attack range per level ('ratr', level n = base + mod*(n-1))."""
    return [("Rhri", REACH_TECH, [("glvl", I, 0, 0, REACH_LEVELS), ("gef1", S, 0, 0, "ratr"),
                                  ("gba1", U, 0, 0, float(REACH_STEP)), ("gmo1", U, 0, 0, float(REACH_STEP)),
                                  ("gnam", S, 0, 0, "Long Reach")])]


# Minion kill gold is paid by the script (MinionBounty: gold = wave number x level), so the wave unit types
# (custom q*** copies and the nc*0 champions) give no built-in bounty.
NO_BOUNTY = [("ubba", I, 0), ("ubdi", I, 0), ("ubsi", I, 0)]


def original_item_mods():
    """Shop items: plenty in stock and quick restock (8 heroes share two shops)."""
    mods = {i: [("isto", I, 8), ("istr", I, 10), ("isst", I, 0)] for i in SHOP_ITEMS}
    for iid, (x, y) in APOTHECARY_SLOTS.items():
        mods[iid] += [("ubpx", I, x), ("ubpy", I, y)]
    for (iid, name, effect, gold, *_rest) in POTIONS:
        mods.setdefault(iid, [])
        mods[iid] += [("unam", S, name), ("utip", S, name), ("ides", S, effect), ("igol", I, gold),
                      ("utub", S, f"{effect}|n|n|cffff8c00Stacks in your inventory|r")]
    return list(mods.items())


# The tavern's Select Unit button would take the first of the 12 hero buttons: it moves off the card. The ability itself stays, it is what sells.
TAVERN_SELECT_HIDDEN = [("abpx", I, 0, 0, 0), ("abpy", I, 0, 0, -11), ("aubx", I, 0, 0, 0), ("auby", I, 0, 0, -11)]


def original_ability_mods():
    """Taverns sell to a player's soul anywhere in the Hall of Champions - no walking needed.
    'Ane2' = tavern Select Unit: aran = range, Neu1 = activation radius (AbilityMetaData.slk). 600 covers the small
    hall (souls 288 from the tavern) and nothing outside it - no champion can buy another hero from a corridor."""
    return [("Ane2", [("aran", U, 1, 0, 600.0), ("Neu1", U, 1, 1, 600.0)] + TAVERN_SELECT_HIDDEN),
            # grove shops (Premium Armory, Bank, Apothecary = 'Aneu'): sell to your champion anywhere on the map
            ("Aneu", [("aran", U, 1, 0, 20000.0), ("Neu1", U, 1, 1, 20000.0)]),
            # Fountain of Power: HP (ACnr/Aoar) and mana (ANre/Aarm) regeneration 1 % -> 2 % of max per second
            ("ACnr", [("Oar1", U, 1, 1, 0.02)]),
            ("ANre", [("Arm1", U, 1, 1, 0.02)])] + [
            # potions: the native fixed heal is zeroed, the script heals the percent (DrinkPotion)
            (ab, [(f, I, 1, d, 0) for (f, d) in fields] + [("acdn", U, 1, 0, cd)])
            for (_i, _n, _e, _g, _hp, _mp, ab, fields, cd) in POTIONS if ab] + xhs_original_abilities()


def custom_items():
    """war3map.w3t custom items: one shop item per kind and price step."""
    out = []
    for si, kd in enumerate(KINDS_DEF):
        castle = is_castle_kind(si)
        for k in range(kind_tiers(si)):
            mods = [("unam", S, f"{kd['name']} +{k * kd['value']} HP/s" if kd["item"] == "Ie" else kd.get("unam", f"{kd['name']} +{kd['value']}")), ("iico", S, kd["icon"]), ("uhot", S, kd["key"]),
                    ("utip", S, kind_title(si, k)),
                    ("utub", S, kind_body(si, k)),
                    ("ides", S, kind_effect(si)),
                    ("igol", I, 0 if castle else stat_price(k, kd.get("price", STAT_BASE_PRICE))),
                    ("ilum", I, CASTLE_TREE_COST if castle else 0), ("isto", I, 1), ("istr", I, 1), ("isst", I, 0),
                    # fixed shop slot (row 1 = Health..Armor, row 2 = Str..All stats). Without it every item
                    # shares the base tome's position and the shop reshuffles them after each buy.
                    ("ubpx", I, kind_slot(si)[0]), ("ubpy", I, kind_slot(si)[1])]
            mods.append(("iabi", S, ""))
            # "abil" kinds keep their ABILITY base in kd["base"]; the item itself must be based on a real
            # item (an ability id as item base crashed 1.27 right after loading) -> a powered-down tome.
            ibase = "tst2"
            out.append((ibase, stat_item_id(si, k), mods))
    for (lvl, iid, aid, name, bonus, icon) in EPIC_ITEMS:
        out.append(("ckng", iid, [
            ("unam", S, name), ("iico", S, CB + icon + ".blp"), ("iabi", S, aid),
            ("utip", S, f"|cffa335eeEPIC|r |cffffcc00{name}|r"),
            ("utub", S, f"+{bonus} Strength, Agility and Intelligence.|n|n|cffa335eeDropped by a Level {lvl} boss.|r"),
            ("ides", S, f"+{bonus} all stats"), ("igol", I, 10000), ("ilev", I, 10), ("ipaw", I, 0)]))
    out.append(("tst2", REACH_ITEM, [
        ("unam", S, "Long Reach"), ("iico", S, CB + "BTNImprovedBows.blp"), ("uhot", S, "Z"),
        ("utip", S, "|cffffcc00Long Reach|r (|cffffcc00Z|r)"),
        ("utub", S, f"+{REACH_STEP} attack range for melee champions|n|n|cffff8c00Melee only, one per champion|r"),
        ("ides", S, f"+{REACH_STEP} attack range (melee only)"), ("iabi", S, ""),
        ("igol", I, REACH_PRICE), ("ilum", I, 0), ("isto", I, 3), ("istr", I, 30), ("isst", I, 0),
        ("ubpx", I, 0), ("ubpy", I, 2)]))
    for i, (tid, (pid, name, effect, gold, *_r)) in enumerate(zip(POTION_TOKENS, POTIONS)):
        out.append(("tst2", tid, [
            ("unam", S, name), ("iico", S, CB + POTION_ICONS[pid] + ".blp"), ("uhot", S, "QWER"[i]),
            ("utip", S, f"|cffffcc00{name}|r (|cffffcc00{'QWER'[i]}|r)"),
            ("utub", S, f"{effect}|n|n|cffff8c00Stacks in your inventory|r"), ("ides", S, effect), ("iabi", S, ""),
            ("igol", I, gold), ("ilum", I, 0), ("isto", I, 8), ("istr", I, 10), ("isst", I, 0),
            ("ubpx", I, i), ("ubpy", I, 0)]))
    out.append(("tst2", BANK_ITEM, [
        ("unam", S, f"Income +{INCOME_STEP}"), ("iico", S, CB + "BTNChestOfGold.blp"), ("uhot", S, "Q"),
        ("utip", S, f"|cffffcc00Income +{INCOME_STEP}|r (|cffffcc00Q|r)"),
        ("utub", S, f"+{INCOME_STEP} gold every minute|n|cff4fc3ffUp to {INCOME_WAVE_SECONDS // 60} minutes per wave of your lane, renewed by your next wave. Always during the final boss.|r|n|n|cffff8c00Costs {INCOME_TREE_COST} tree|r"),
        ("ides", S, f"+{INCOME_STEP} gold every minute, up to {INCOME_WAVE_SECONDS // 60} minutes per wave of your lane"), ("iabi", S, ""),
        ("igol", I, 0), ("ilum", I, INCOME_TREE_COST), ("isto", I, 20), ("istr", I, 1), ("isst", I, 0),
        ("ubpx", I, 0), ("ubpy", I, 0)]))
    for i, (name, base, icon, _ab, _f, _vals, _what, _rows) in enumerate(PREMIUM_DEF):
        key = PREMIUM_KEYS[i]
        for L in range(1, PREMIUM_LEVELS + 1):
            text = premium_text(i, L)
            rank = f"|cff4fc3ffRank {L}/{PREMIUM_LEVELS}|r"
            mods = [("unam", S, name if L == 1 else f"{name} Rank {L}"), ("iico", S, CB + icon + ".blp"),
                    ("utub", S, text), ("ides", S, text),
                    ("iabi", S, premium_abil_id(i, L)), ("igol", I, PREMIUM_PRICE), ("ilum", I, 0)]
            if L == 1:      # the shop item
                mods += [("uhot", S, key), ("utip", S, f"|cffffcc00{name}|r [|cffffcc00{key}|r] {rank}"),
                         ("isto", I, PREMIUM_STOCK), ("istr", I, 30), ("isst", I, 0), ("ubpx", I, i % 4), ("ubpy", I, i // 4)]
            else:
                mods += [("utip", S, f"|cffffcc00{name}|r {rank}")]
            out.append((base, premium_item_id(i, L), mods))
    return out + boss_gear_items()


def custom_abilities():
    """war3map.w3a custom table: hidden stacking bonus abilities, one per buy ("abil" kinds)."""
    out = []
    for si, kd in enumerate(KINDS_DEF):
        if kd["type"] not in ("abil", "castleabil"):
            continue
        for k in range(STAT_TIERS):
            out.append((kd["base"], bonus_abil_id(si, k), [(f, I, 1, dp, kd["value"]) for f, dp in kd["fields"]]))
    # the castle's allied-shop ability: activation radius + range cover the whole plaza
    out.append(("Aneu", CASTLE_SHOP_ABIL, [("aran", U, 1, 0, CASTLE_SHOP_RANGE), ("Neu1", U, 1, 1, CASTLE_SHOP_RANGE)]))
    out.append(("Aall", CASTLE_SHARE_ABIL, [("aran", U, 1, 0, CASTLE_SHOP_RANGE), ("Neu1", U, 1, 1, CASTLE_SHOP_RANGE)]))
    out += xhs_custom_abilities()
    out += boss_spell_abilities()
    out += boss_gear_abilities()
    out += final_boss_abilities()
    for (_lvl, _iid, aid, _name, bonus, _icon) in EPIC_ITEMS:      # epic crown: +all stats (green)
        out.append(("AIx1", aid, [("Iagi", I, 1, 1, bonus), ("Iint", I, 1, 2, bonus), ("Istr", I, 1, 3, bonus)]))
    out += scale_abilities()
    vt = {"U": U, "I": I}
    for i, (_n, _b, _i, abase, fields, vals, _what, _rows) in enumerate(PREMIUM_DEF):
        for L in range(1, PREMIUM_LEVELS + 1):
            out.append((abase, premium_abil_id(i, L),
                        [(f, vt[ty], 1, dp, v) for (f, ty, dp), v in zip(fields, vals(L))]))
    return out
