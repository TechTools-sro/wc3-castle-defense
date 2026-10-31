"""Custom objects (war3map.w3u / war3map.w3t) + wave rosters, v2 (hero lane defense).

Field ids / value types verified against Units\\UnitMetaData.slk of 1.27:
int=0, real=1, unreal=2, string-ish (string, model, icon, lists, armor/attack type)=3.
"""
from w3files import VT_INT as I, VT_REAL as R, VT_UNREAL as U, VT_STRING as S

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

# The Dark Gate (shared NE lane, arm index 4 in the script): stronger tower + Nexus, waves two tiers up.
SHARED = {"name": "The Dark Gate", "color": "|cffff4040",
          "base": ("unp2", "Dark Citadel"), "turret": ("uzg1", "Dark Spire"),
          "tiers": [("nska", "ugho"), ("nskm", "nsko"), ("ucry", "nsog"),
                    ("ngh2", "uabo"), ("ufro", "nerw"), ("ninf", "nbal")],
          "stages": [("ngh2", "uabo"), ("ninf", "nbal"), ("ninf", "nbal")],
          "champion": "nrvd"}
SHARED_BASE_HP, SHARED_BASE_ARMOR = 80000, 15     # 10x the old 8000
SHARED_NEXUS_DMG = (650, 4, 25)
SHARED_TURRET_HP, SHARED_TURRET_ARMOR, SHARED_TURRET_DMG = 4000, 8, (140, 2, 15)
SHARED_TINT = (255, 90, 90)

# Wave size (same for every lane and stage): front line = melee, back line = ranged.
WAVE_FRONT_BASE = 4          # front = 4 + wave  (wave 1 -> 5, +1 per wave)
WAVE_BACK_DIV = 2            # back  = wave / 2  (+1 every 2 waves)
WAVE_FRONT_MAX, WAVE_BACK_MAX = 30, 15     # per lane, keeps 8 lanes playable late
# Champions join every 10th wave: wave 10 -> 1, wave 20 -> 2, ... per lane, as weakened copies (nc{d}0).
WAVE_CHAMP_EVERY = 10
WAVE_CHAMP_HP, WAVE_CHAMP_ARMOR, WAVE_CHAMP_DMG, WAVE_CHAMP_SCALE = 800, 2, (30, 1, 8), 1.0

# Champion select: 4 race taverns + the standard neutral tavern.
TAVERNS = [
    ("tvh0", "Hall of the Alliance", ["Hpal", "Hamg", "Hmkg", "Hblm"]),
    ("tvo0", "Hall of the Horde", ["Obla", "Ofar", "Otch", "Oshd"]),
    ("tvu0", "Hall of the Scourge", ["Udea", "Ulic", "Udre", "Ucrl"]),
    ("tve0", "Hall of the Sentinels", ["Edem", "Ekee", "Emoo", "Ewar"]),
    ("tvn0", "Hall of Mercenaries", ["Nalc", "Ntin", "Nfir", "Nngs", "Nbrn", "Npbm", "Nplh", "Nbst"]),
]
ALL_HEROES = [h for (_, _, hs) in TAVERNS for h in hs]

# Premium Armory (secret grove): 8 simple, special items for 1000 gold each. Each = a real base item (class/model)
# + one custom ability cloned from a real item ability with a stronger value.
#   (item id, base item, name, effect line, icon, ability base, ability id, [(field, type, data ptr, value)])
PREMIUM_PRICE = 1000
# Upgradable: buying an item you already hold merges both into the next level (Lv 1..PREMIUM_LEVELS).
# Each level = its own item type + ability with stronger values; only Lv 1 is sold.
#   (name, base item, icon, ability base, [(field, type, data ptr)], values(L) -> [one per field], effect(L) -> text)
PREMIUM_LEVELS = 5
PREMIUM_DEF = [
    ("Vampire Fang", "modt", "BTNMaskOfDeath", "AIva", [("Ivam", "U", 1)],
     lambda L: [0.30 + 0.10 * (L - 1)], lambda L: f"{30 + 10 * (L - 1)}% lifesteal"),
    ("Fury Gloves", "gcel", "BTNGlove", "AIsx", [("Isx1", "U", 1)],
     lambda L: [0.40 + 0.15 * (L - 1)], lambda L: f"+{40 + 15 * (L - 1)}% attack speed"),
    ("Executioner's Axe", "ratc", "BTNCriticalStrike", "AIcs", [("Ocr1", "U", 1), ("Ocr2", "U", 2), ("Ocr3", "U", 3), ("Ocr4", "U", 4)],
     lambda L: [20.0 + 5 * (L - 1), 3.0, 0.0, 0.0], lambda L: f"{20 + 5 * (L - 1)}% chance for 3x damage"),
    ("Stormhammer", "ratc", "BTNBash", "AIbx", [("Hbh1", "U", 1), ("Hbh3", "U", 3), ("adur", "U", 0), ("ahdu", "U", 0)],
     lambda L: [20.0 + 5 * (L - 1), 40.0 + 20 * (L - 1), 1.0, 1.0],
     lambda L: f"{20 + 5 * (L - 1)}% chance to stun 1 s, +{40 + 20 * (L - 1)} damage"),
    ("Phantom Cloak", "evtl", "BTNEvasion", "AIev", [("Eev1", "U", 1)],
     lambda L: [0.25 + 0.05 * (L - 1)], lambda L: f"{25 + 5 * (L - 1)}% chance to dodge attacks"),
    ("Winged Boots", "bspd", "BTNBootsOfSpeed", "AIms", [("Imvb", "I", 1)],
     lambda L: [100 + 25 * (L - 1)], lambda L: f"+{100 + 25 * (L - 1)} movement speed"),
    ("Troll Heart", "rlif", "BTNRegenerate", "Arel", [("Ihpr", "I", 1)],
     lambda L: [15 + 10 * (L - 1)], lambda L: f"+{15 + 10 * (L - 1)} HP per second"),
    ("Arcane Mask", "rwiz", "BTNSobiMask", "AIrm", [("Imrp", "U", 1)],
     lambda L: [1.5 + 0.5 * (L - 1)], lambda L: f"+{150 + 50 * (L - 1)}% mana regeneration"),
]


def premium_item_id(i, L):       # Lv 1 = the shop item Ip01..Ip08, higher levels Iu<i><L>
    return f"Ip0{i + 1}" if L == 1 else f"Iu{i + 1}{L}"


def premium_abil_id(i, L):
    return f"Xp0{i + 1}" if L == 1 else f"Xu{i + 1}{L}"


PREMIUM = [(premium_item_id(i, 1),) for i in range(len(PREMIUM_DEF))]   # shop list (Lv 1 ids)
PREMIUM_KEYS = "QWERASDF"

# Bank (secret grove): trade trees (lumber, +1 per cleared wave) for passive income.
BANK_ITEM = "Ib01"
INCOME_STEP = 100            # gold per minute per bought income
INCOME_TREE_COST = 1

SHOPS = {
    "armory": ("shpa", "Premium Armory", [p[0] for p in PREMIUM]),
    "bank": ("shpc", "Bank", [BANK_ITEM]),
    "apothecary": ("shpb", "Apothecary", ["phea", "pman", "pghe", "pgma", "pres", "plcl",
                                          "bspd", "prvt", "rlif", "rwiz", "stel", "pnvl"]),
}
SHOP_ITEMS = sorted({i for (_, _, items) in SHOPS.values() for i in items} - {p[0] for p in PREMIUM} - {BANK_ITEM})   # originals only

CASTLE_ID = "hcd0"
# The castle is owned by Player 15 (neutral "extra" slot). Its shop gets BOTH buyer-selection abilities with a
# plaza-wide radius: a neutral-building one (like the grove shops) and an allied shop-sharing one.
CASTLE_SHOP_ABIL = "Xcsh"     # custom 'Aneu' (Neutral Building: select hero)
CASTLE_SHARE_ABIL = "Xcs2"    # custom 'Aall' (Shop Sharing, Allied Bldg.)
CIRCLE_ID = "ncd3"           # the player's coloured circle at his lane entrance = stat shop

# Stat shop at the lane circle (the player's own shop). Every item is instant and each buy costs 10 % more:
# every price step is its own item type, the script swaps the stock when the item is picked up.
# Shop slots fill in order -> row 1 = Health Mana Damage Armor, row 2 = Strength Agility Intelligence All stats.
#   every kind is type "abil": the script adds the next copy of a hidden item-bonus ability to the hero
#   (copies with different ids stack). Attribute bonuses this way show as GREEN +N, not in the base value.
STAT_PER_LEVEL = 10     # single stats (Str / Agi / Int)
ALL_STATS_VALUE = 3     # the "All stats" buy
CB = "ReplaceableTextures\\CommandButtons\\"
STAT_ICON = {"str": CB + "BTNCDStr.blp", "agi": CB + "BTNCDAgi.blp", "int": CB + "BTNCDInt.blp"}   # imported (gen/icons.py)
# item-bonus ability fields (AbilityMetaData.slk): Iagi = data 1, Iint = data 2, Istr = data 3
KINDS_DEF = [
    {"item": "Ih", "name": "Health", "base": "AIlf", "fields": [("Ilif", 1)], "value": 100, "key": "Q", "icon": CB + "BTNHeal.blp", "abil": "Xh"},
    {"item": "Im", "name": "Mana", "base": "AImb", "fields": [("Iman", 1)], "value": 75, "key": "W", "icon": CB + "BTNBrilliance.blp", "abil": "Xm"},
    {"item": "Id", "name": "Damage", "base": "AIat", "fields": [("Iatt", 1)], "value": 5, "key": "E", "icon": CB + "BTNAttack.blp", "abil": "Xd"},
    {"item": "Ir", "name": "Armor", "base": "AId1", "fields": [("Idef", 1)], "value": 2, "key": "R", "icon": CB + "BTNDefend.blp", "abil": "Xa"},
    {"item": "Is", "name": "Strength", "base": "AIs1", "fields": [("Istr", 3)], "value": STAT_PER_LEVEL, "key": "A", "icon": STAT_ICON["str"], "abil": "Xs"},
    {"item": "Ia", "name": "Agility", "base": "AIa1", "fields": [("Iagi", 1)], "value": STAT_PER_LEVEL, "key": "S", "icon": STAT_ICON["agi"], "abil": "Xg"},
    {"item": "Ii", "name": "Intelligence", "base": "AIi1", "fields": [("Iint", 2)], "value": STAT_PER_LEVEL, "key": "D", "icon": STAT_ICON["int"], "abil": "Xi"},
    {"item": "Il", "name": "All stats", "base": "AIx1", "fields": [("Iagi", 1), ("Iint", 2), ("Istr", 3)], "value": ALL_STATS_VALUE, "key": "F", "icon": CB + "BTNStatUp.blp", "abil": "Xl"},
]
for _kd in KINDS_DEF:
    _kd["type"] = "abil"
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
     "key": "A", "slot": (0, 1), "icon": CB + "BTNShockWave.blp", "effect": "Shockwave: 300 + 30 per wave damage to all monsters near the castle"},
]
CASTLE_TREE_COST = 1          # every castle upgrade costs 1 tree (lumber), no gold
KINDS = len(KINDS_DEF)
KIND_TYPE = {"abil": 1, "castleheal": 3, "castleabil": 4, "castleshock": 5}
STAT_TIERS = 40
STAT_BASE_PRICE, STAT_PRICE_GROWTH = 100, 1.10


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
    """Fixed button (x, y). Circle: rows 1-2 = the 8 hero kinds. Castle shop: its own "slot"."""
    if is_castle_kind(s):
        return KINDS_DEF[s]["slot"]
    return (s % 4, s // 4)


def kind_effect(s):
    kd = KINDS_DEF[s]
    return kd.get("effect", f"+{kd['value']} {kd['name']}")
SOUL_ID = "ecd0"


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


def wave_champion_id(d):     # weakened faction champion for waves (d = 4: the Dark Gate)
    return f"nc{d}0"


def boss_id(d, k):           # k = player-count tier: 0 (1-2 players), 1 (3-5), 2 (6-8)
    return f"nb{d}{k}"


BASE_HP, BASE_ARMOR = 30000, 10      # 10x the old 3000: the Nexus is the lane's big final obstacle
# Every Nexus fights back (huge attack, out of the tower's reach - see layout.tower_pos)
NEXUS_DMG, NEXUS_COOLDOWN, NEXUS_RANGE = (450, 4, 20), 2.5, 700
NEXUS_MISSILE = "Abilities\\Weapons\\FrostWyrmMissile\\FrostWyrmMissile.mdl"
TURRET_HP, TURRET_ARMOR, TURRET_DMG = 1800, 4, (85, 2, 10)   # ~96 chaos per hit / 1.3 s: strong vs early heroes
BOSS_HP = [3500, 6000, 9000]
BOSS_ARMOR = [3, 4, 5]
BOSS_DMG = [(28, 2, 8), (38, 2, 10), (48, 2, 12)]


def custom_units():
    units = []
    no_bounty = [("ubba", I, 0), ("ubdi", I, 0), ("ubsi", I, 0)]
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
    units.append(("ncp3", CIRCLE_ID, [
        ("unam", S, "Champion's Circle"), ("uabi", S, "Avul,Aall,Apit,Asid"), ("usei", S, ""),
        ("utip", S, "Champion's Circle"),
        ("utub", S, "Your lane. Buy +2 Strength / Agility / Intelligence for your champion here - instant; every buy costs 10% more.")]))
    for (tid, name, heroes) in TAVERNS:
        units.append(("ntav", tid, [("unam", S, name), ("useu", S, ",".join(heroes))]))
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
            ("uabi", S, ""), ("utra", S, ""), ("ures", S, ""), ("uupt", S, "")] + nexus_attack(NEXUS_DMG) + [
            ("usid", I, 1000), ("usin", I, 1000), ("ubba", I, 200), ("ubdi", I, 1), ("ubsi", I, 1)]))
        base, dice, sides = TURRET_DMG
        units.append((tb, turret_id(d), [
            ("unam", S, tname), ("uhpm", I, TURRET_HP), ("udef", I, TURRET_ARMOR), ("udty", S, "fort"),
            ("ua1b", I, base), ("ua1d", I, dice), ("ua1s", I, sides), ("ua1c", U, 1.3),
            ("ua1r", I, 750), ("uacq", U, 800.0), ("ua1t", S, "chaos"), ("uabi", S, ""),
            ("usid", I, 1000), ("usin", I, 1000), ("usca", R, 1.25),
            ("ubba", I, 100), ("ubdi", I, 1), ("ubsi", I, 1)]))
        if d == 0:     # once, next to the factions: the Dark Gate's tower + Nexus (ids ns40 / nt40)
            tr, tg, tb = SHARED_TINT
            units.append((SHARED["base"][0], base_id(4), [
                ("unam", S, SHARED["base"][1]), ("uhpm", I, SHARED_BASE_HP), ("udef", I, SHARED_BASE_ARMOR),
                ("udty", S, "fort"), ("uabi", S, ""), ("utra", S, ""), ("ures", S, ""), ("uupt", S, "")] + nexus_attack(SHARED_NEXUS_DMG) + [
                ("usid", I, 1000), ("usin", I, 1000), ("ubba", I, 500), ("ubdi", I, 1), ("ubsi", I, 1),
                ("usca", R, 1.2), ("uclr", I, tr), ("uclg", I, tg), ("uclb", I, tb)]))
            sb, sd, ss = SHARED_TURRET_DMG
            units.append((SHARED["turret"][0], turret_id(4), [
                ("unam", S, SHARED["turret"][1]), ("uhpm", I, SHARED_TURRET_HP), ("udef", I, SHARED_TURRET_ARMOR),
                ("udty", S, "fort"), ("ua1b", I, sb), ("ua1d", I, sd), ("ua1s", I, ss), ("ua1c", U, 1.3),
                ("ua1r", I, 800), ("uacq", U, 850.0), ("ua1t", S, "chaos"), ("uabi", S, ""),
                ("usid", I, 1000), ("usin", I, 1000), ("usca", R, 1.5), ("uclr", I, tr), ("uclg", I, tg), ("uclb", I, tb),
                ("ubba", I, 200), ("ubdi", I, 1), ("ubsi", I, 1)]))
        for k in range(3):
            base, dice, sides = BOSS_DMG[k]
            mods = [
                ("unam", S, b["name"]), ("uhpm", I, BOSS_HP[k]), ("udef", I, BOSS_ARMOR[k]),
                ("udty", S, "hero"), ("uhpr", U, 2.0), ("uhrt", S, "always"),
                ("umpm", I, 1000), ("umpi", I, 1000), ("umpr", U, 4.0),
                ("ua1b", I, base), ("ua1d", I, dice), ("ua1s", I, sides), ("ua1c", U, 1.6),
                ("ua1r", I, b["range"]), ("uacq", U, 700.0), ("ua1t", S, "chaos"),
                ("uabi", S, b["abils"]), ("usca", R, b["scale"]), ("ussc", R, 3.0),
                ("ucol", U, 40.0), ("umvs", I, 240), ("ulev", I, 10), ("usid", I, 1000), ("usin", I, 1000),
                ("ubba", I, 300), ("ubdi", I, 1), ("ubsi", I, 1),
            ]
            for key, fid in (("model", "umdl"), ("icon", "uico"), ("missile", "ua1m"), ("sound", "usnd")):
                if key in b:
                    mods.append((fid, S, b[key]))
            units.append((b["base"], boss_id(d, k), mods))
    # weakened wave champions (every 10th wave): half damage, about half HP, smaller model
    for d, f in enumerate(FACTIONS + [SHARED]):
        units.append((f["champion"], wave_champion_id(d), [
            ("uhpm", I, WAVE_CHAMP_HP), ("udef", I, WAVE_CHAMP_ARMOR), ("ua1b", I, WAVE_CHAMP_DMG[0]),
            ("ua1d", I, WAVE_CHAMP_DMG[1]), ("ua1s", I, WAVE_CHAMP_DMG[2]), ("usca", R, WAVE_CHAMP_SCALE)]))
    return units


# Hero levels: practically unlimited (MAX_HERO_LEVEL in war3mapMisc.txt). Spells are maxed at level 10
# (3+3+3+1 points); from level 11 every skill point goes into "Attributes" (+3 Str/Agi/Int per level).
MAX_HERO_LEVEL = 1000
ATTR_ABIL = "Xatt"            # custom hero ability based on 'Aamk' (Attribute Bonus)
ATTR_PER_LEVEL = 3
ATTR_LEVELS = 100             # learnable at hero levels 11..110; above that the script adds the stats itself
ATTR_REQ_LEVEL = 11


def _ref_slk(name):
    import os
    from slk import read_slk
    cache = globals().setdefault("_REF_CACHE", {})
    if name not in cache:
        cache[name] = read_slk(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ref", name))
    return cache[name]


def attribute_ability():
    """('Aamk', ATTR_ABIL, mods): 100 levels, each level = +3 more Str/Agi/Int (values are cumulative)."""
    mods = [("alev", I, 0, 0, ATTR_LEVELS), ("arlv", I, 0, 0, ATTR_REQ_LEVEL), ("alsk", I, 0, 0, 1),
            ("aher", I, 0, 0, 1), ("arhk", S, 0, 0, "T"), ("arpx", I, 0, 0, 0), ("arpy", I, 0, 0, 1),
            ("abpx", I, 0, 0, 2), ("abpy", I, 0, 0, 1),
            ("aart", S, 0, 0, CB + "BTNStatUp.blp"), ("arar", S, 0, 0, CB + "BTNStatUp.blp"),
            ("aret", S, 0, 0, "|cffffcc00[T]|r Learn |cffffcc00Attributes|r - Level %d"),
            ("arut", S, 0, 0, f"+{ATTR_PER_LEVEL} Strength, Agility and Intelligence per level.|n|cffff8c00From hero level {ATTR_REQ_LEVEL} (spells maxed).|r")]
    for lvl in range(1, ATTR_LEVELS + 1):
        v = ATTR_PER_LEVEL * lvl
        mods += [("Iagi", I, lvl, 1, v), ("Iint", I, lvl, 2, v), ("Istr", I, lvl, 3, v),
                 ("atp1", S, lvl, 0, f"Attributes - Level {lvl}"), ("aub1", S, lvl, 0, f"+{v} Strength, Agility and Intelligence.")]
    return ("Aamk", ATTR_ABIL, mods)


def _hero_targets_with_air(h):
    """Attack-1 target list of hero h (Units/UnitWeapons.slk) with "air" added: melee heroes must hit flyers too."""
    import os
    from slk import read_slk
    global _WEAPONS
    if "_WEAPONS" not in globals():
        _WEAPONS = read_slk(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ref", "Units_UnitWeapons.slk"))
    targs = [x for x in _WEAPONS[h]["targs1"].split(",") if x]
    if "air" not in targs:
        targs.insert(targs.index("debris") + 1 if "debris" in targs else len(targs), "air")
    return ",".join(targs)


def original_unit_mods():
    """Edits to standard units: tavern heroes are free, cost no food and are in stock at once;
    every hero (melee too) can attack air units."""
    # ureq "" : the 8 tavern (neutral) heroes require an Altar ('TALT') in melee - nobody has one here
    return [(h, [("ugol", I, 0), ("ulum", I, 0), ("ufoo", I, 0), ("usst", I, 0),
                 ("usma", I, 1), ("usrg", I, 1), ("ureq", S, ""),
                 ("ua1g", S, _hero_targets_with_air(h)),
                 ("uhab", S, _ref_slk("Units_UnitAbilities.slk")[h]["heroAbilList"] + "," + ATTR_ABIL)]) for h in ALL_HEROES]


def original_item_mods():
    """Shop items: plenty in stock and quick restock (8 heroes share two shops)."""
    return [(i, [("isto", I, 8), ("istr", I, 10), ("isst", I, 0)]) for i in SHOP_ITEMS]


def original_ability_mods():
    """Taverns sell to a player's soul anywhere in the Hall of Champions - no walking needed.
    'Ane2' = tavern Select Unit: aran = range, Neu1 = activation radius (AbilityMetaData.slk)."""
    return [("Ane2", [("aran", U, 1, 0, 1600.0), ("Neu1", U, 1, 1, 1600.0)]),
            # Fountain of Power: HP (ACnr/Aoar) and mana (ANre/Aarm) regeneration 1 % -> 2 % of max per second
            ("ACnr", [("Oar1", U, 1, 1, 0.02)]),
            ("ANre", [("Arm1", U, 1, 1, 0.02)])]


def custom_items():
    """war3map.w3t custom items: one shop item per kind and price step."""
    out = []
    for si, kd in enumerate(KINDS_DEF):
        castle = is_castle_kind(si)
        for k in range(kind_tiers(si)):
            mods = [("unam", S, f"{kd['name']} +{kd['value']}"), ("iico", S, kd["icon"]), ("uhot", S, kd["key"]),
                    ("utip", S, f"{kd['name']}  |cff4fc3ffLv {k}|r  (|cffffcc00{kd['key']}|r)"),   # Lv = times already bought
                    ("utub", S, f"{kind_effect(si)}|n|n" + (f"|cff80ff80Costs {CASTLE_TREE_COST} tree|r" if castle
                                                              else "|cffff8c00Next buy: +10% gold|r")),
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
    out.append(("tst2", BANK_ITEM, [
        ("unam", S, f"Income +{INCOME_STEP}"), ("iico", S, CB + "BTNChestOfGold.blp"), ("uhot", S, "Q"),
        ("utip", S, f"|cffffcc00Income +{INCOME_STEP}|r (|cffffcc00Q|r)"),
        ("utub", S, f"+{INCOME_STEP} gold every minute|n|n|cffff8c00Costs {INCOME_TREE_COST} tree|r"),
        ("ides", S, f"+{INCOME_STEP} gold every minute"), ("iabi", S, ""),
        ("igol", I, 0), ("ilum", I, INCOME_TREE_COST), ("isto", I, 20), ("istr", I, 1), ("isst", I, 0),
        ("ubpx", I, 0), ("ubpy", I, 0)]))
    for i, (name, base, icon, _ab, _f, _vals, effect) in enumerate(PREMIUM_DEF):
        key = PREMIUM_KEYS[i]
        for L in range(1, PREMIUM_LEVELS + 1):
            hint = "|cff80ff80Max level|r" if L == PREMIUM_LEVELS else f"|cffff8c00Buy again to upgrade (max Lv {PREMIUM_LEVELS})|r"
            mods = [("unam", S, name if L == 1 else f"{name} Lv {L}"), ("iico", S, CB + icon + ".blp"),
                    ("utub", S, f"{effect(L)}|n|n{hint}"), ("ides", S, effect(L)),
                    ("iabi", S, premium_abil_id(i, L)), ("igol", I, PREMIUM_PRICE), ("ilum", I, 0)]
            if L == 1:      # the shop item
                mods += [("uhot", S, key), ("utip", S, f"|cffffcc00{name}|r (|cffffcc00{key}|r)"),
                         ("isto", I, 3), ("istr", I, 30), ("isst", I, 0), ("ubpx", I, i % 4), ("ubpy", I, i // 4)]
            else:
                mods += [("utip", S, f"|cffffcc00{name}|r  |cff4fc3ffLv {L}|r")]
            out.append((base, premium_item_id(i, L), mods))
    return out


def custom_abilities():
    """war3map.w3a custom table: hidden stacking bonus abilities, one per buy ("abil" kinds)."""
    out = []
    for si, kd in enumerate(KINDS_DEF):
        if kd["type"] not in ("abil", "castleabil"):
            continue
        for k in range(STAT_TIERS):
            out.append((kd["base"], bonus_abil_id(si, k), [(f, I, 1, dp, kd["value"]) for f, dp in kd["fields"]]))
    # the castle's allied-shop ability: activation radius + range cover the whole plaza
    out.append(("Aneu", CASTLE_SHOP_ABIL, [("aran", U, 1, 0, 3000.0), ("Neu1", U, 1, 1, 3000.0)]))
    out.append(("Aall", CASTLE_SHARE_ABIL, [("aran", U, 1, 0, 3000.0), ("Neu1", U, 1, 1, 3000.0)]))
    out.append(attribute_ability())
    vt = {"U": U, "I": I}
    for i, (_n, _b, _i, abase, fields, vals, _e) in enumerate(PREMIUM_DEF):
        for L in range(1, PREMIUM_LEVELS + 1):
            out.append((abase, premium_abil_id(i, L),
                        [(f, vt[ty], 1, dp, v) for (f, ty, dp), v in zip(fields, vals(L))]))
    return out
