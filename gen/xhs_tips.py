"""What the 12 champions' abilities say in the game, generated from the numbers they really have (gen/xhs_data.py over the game's own tables).

A tooltip cannot disagree with its ability: every value is read from the field the engine uses. SPEC only says what the field means.

    what    one line: the real effect
    rows    (label, value per rank). A value that changes with the rank is a row of its own, all ranks side by side;
            one that does not goes into a short line of constants
    after   what scripts add on top (hero level 20 and so on)

Normal tooltip, one text per rank: the current rank in gold, learned ranks light grey, future ones grey; orange only says what comes next.
Learn tooltip, one text for all ranks (the engine has no per-rank Learn text): every rank in plain white, the offered rank only in the title (native %d).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import xhs_data as XHS       # noqa: E402

GOLD, BLUE, ORANGE, GREEN = "|cffffcc00", "|cff4fc3ff", "|cffff8c00", "|cff80ff80"
GREY, DONE = "|cff808080", "|cffc0c0c0"
MAX_RAW = 900               # an ability text of 1059 bytes crashes the game while the map loads, 973 does not (docs/wc3-127-gotchas.md)
LINE_CHARS = 44             # what fits one line of the tooltip box, seen in hidden pictures; a longer line wraps, nothing is lost
_tables = {}


def _table(name):
    if name not in _tables:
        from slk import read_slk
        _tables[name] = read_slk(os.path.join(os.path.dirname(HERE), "ref", name))
    return _tables[name]


def _number(value):
    text = str(value).strip()
    if text in ("", "-", "_"):
        return 0.0
    return float(text)


def _ability(aid):
    entry = XHS.ABILS.get(aid)
    return (entry[0], entry[2]) if entry else (aid, [])


def levels(aid):
    base, mods = _ability(aid)
    for (field, _k, _l, _p, value) in mods:
        if field == "alev":
            return int(value)
    return int(_table("Units_AbilityData.slk")[base]["levels"])


def _column(field):
    meta = _table("Units_AbilityMetaData.slk")[field]
    name = meta["field"]
    return "Data" + "ABCDEFGHI"[int(meta["data"]) - 1] if name == "Data" else name


def raw(aid, field, level):
    """The value of a field at a rank: the map's, else the game's own table."""
    base, mods = _ability(aid)
    for (f, _k, lvl, _p, value) in mods:
        if f == field and lvl == level:
            return value
    return _table("Units_AbilityData.slk")[base].get(f"{_column(field)}{level}", "")


def val(aid, field, level):
    return _number(raw(aid, field, level))


def fmt(number):
    number = round(number, 3)
    return str(int(number)) if number == int(number) else f"{number:g}"


def hero_level(aid, rank):
    base, mods = _ability(aid)
    row = _table("Units_AbilityData.slk")[base]
    req, skip = int(_number(row.get("reqLevel"))), int(_number(row.get("levelSkip")))
    for (f, _k, _l, _p, value) in mods:
        if f == "arlv":
            req = int(value)
        elif f == "alsk":
            skip = int(value)
    return req + (rank - 1) * (skip or 2)        # a skip of 0 is the game's HeroAbilityLevelSkip, 2


# ---- what a row reads
def V(field, unit="", pre="", mult=1.0):
    return lambda aid, rank: f"{pre}{fmt(val(aid, field, rank) * mult)}{unit}"


def P(field, pre=""):
    """A field that holds a fraction: 0.15 is 15 %."""
    return V(field, "%", pre, 100.0)


def PLUS(field):
    return P(field, "+")


def ADD(field, unit=""):
    return V(field, unit, "+")


def LIT(*values):
    return lambda _aid, rank: values[rank - 1]


def _summon_of(aid, rank):
    base, mods = _ability(aid)
    meta = _table("Units_AbilityMetaData.slk")
    for (f, _k, lvl, _p, value) in mods:
        if lvl == rank and meta.get(f, {}).get("field") == "UnitID":
            return value
    return _table("Units_AbilityData.slk")[base].get(f"UnitID{rank}", "")


def unit_stats(uid):
    """HP, damage per hit (average of the dice), seconds between attacks: the map's, else the game's own."""
    entry = XHS.UNITS.get(uid)
    base = entry[0] if entry else uid
    mods = {f: v for (f, _k, _l, _p, v) in (entry[2] if entry else [])}
    balance, weapon = _table("Units_UnitBalance.slk").get(base, {}), _table("Units_UnitWeapons.slk").get(base, {})
    hp = _number(mods.get("uhpm", balance.get("HP")))
    plus = _number(mods.get("ua1b", weapon.get("dmgplus1")))
    dice = _number(mods.get("ua1d", weapon.get("dice1")))
    sides = _number(mods.get("ua1s", weapon.get("sides1")))
    return hp, plus + dice * (sides + 1) / 2.0, _number(mods.get("ua1c", weapon.get("cool1")))


def UNIT_HP(of=_summon_of):
    return lambda aid, rank: fmt(unit_stats(of(aid, rank))[0])


def UNIT_HIT(of=_summon_of):
    return lambda aid, rank: fmt(unit_stats(of(aid, rank))[1])


def UNIT_EVERY(of=_summon_of):
    return lambda aid, rank: f"{fmt(unit_stats(of(aid, rank))[2])} s"


def _beetle(aid, rank):
    return raw(aid, "Rai3", rank)


def _fixed(uid):
    return lambda _aid, _rank: uid


MANA = ("Mana", V("amcs"))
CD = ("Cooldown", V("acdn", " s"))
RNG = ("Range", V("aran"))
RAD = ("Radius", V("aare"))
LASTS = ("Lasts", V("adur", " s"))
HERO_LASTS = ("Lasts", V("ahdu", " s"))


def _strike(aid, field):
    return fmt(val(aid, field, 1))


_SECOND_BOLT = f"{BLUE}Hero level 20:|r a second bolt, +{_strike('A02V', 'Ctb1')} damage."
_SECOND_CLAP = f"{BLUE}Hero level 20:|r a second clap, +{_strike('A04P', 'Ctc1')} damage."
_SECOND_WAVE = f"{BLUE}Hero level 20, Roar on:|r a second wave, +{_strike('A04Q', 'Ucs1')}."
_SECOND_STOMP = f"{BLUE}Hero level 20, Roar on:|r a second stomp, +{_strike('A01O', 'Ctc1')}."
_DRUMS = ("A033", "A046", "A047", "A048")


def _drums(_aid, rank):
    return f"+{fmt(val(_DRUMS[rank - 1], 'Akb1', 1) * 100)}%"


def _drums_radius(_aid, rank):
    return fmt(val(_DRUMS[rank - 1], "aare", 1))


_CRIT = ("A chance of a stronger hit.", [("Chance", V("Ocr1", "%")), ("Damage", V("Ocr2", pre="x"))])
_DODGE = ("Attacks against you miss.", [("Dodge", P("Eev1"))])
_ENDURANCE = ("Allies near you move and attack faster.", [("Move", PLUS("Oae1")), ("Attack", PLUS("Oae2")), RAD])
_TRUESHOT = ("Allies near you deal more with ranged attacks.", [("Ranged", PLUS("Ear1")), RAD])
_VAMPIRE = ("Melee allies near you heal by a share of the attack damage they deal.", [("Lifesteal", P("Uav1")), RAD])
_POISON = ("Your attacks poison and slow.", [("Poison per s", V("Poi1")), LASTS, ("Slows attack", P("Poi2")), ("Slows move", P("Poi3"))])
_STOMP = ("Slam: damage and a stun around you.", [("Damage", V("Wrs1")), ("Radius", V("aare")), MANA, CD, ("Stun", V("adur", " s"))])
_CHAOS = ("Channel: enemies in the area lose a share of their max HP.", [("Max HP per s", P("Udd1")), LASTS, RAD, MANA, CD, RNG])
_COUNT = ("Count", V("Hwe2"))
_SUMMON_ROWS = [_COUNT, ("HP each", UNIT_HP()), ("Avg hit", UNIT_HIT()), LASTS, MANA, CD]

SPEC = {
    # Dryad
    "A028": _DODGE,
    "A02A": ("Every attack also throws spears at other enemies nearby, each with your weapon's damage. Faster attacks, more volleys. One lone enemy: one hit.",
             [("Targets incl. primary", LIT("4", "6", "8", "up to 10")), RAD]),
    "A000": _CRIT,
    "A029": _TRUESHOT,
    "AOae": _ENDURANCE,
    "ACvs": _POISON,
    "A027": ("Immune to spells.", []),
    # Mountain King
    "AHtb": ("A hammer: damage and a stun on one enemy.", [("Damage", V("Htb1")), MANA, ("Stun", V("adur", " s")), CD, RNG], _SECOND_BOLT),
    "AHtc": ("Slam: damage and a slow around you.", [("Damage", V("Htc1")), ("Radius", V("aare")), ("Slow lasts", V("adur", " s")), MANA,
                                                       ("Slows move", P("Htc3")), ("Slows attack", P("Htc4")), CD], _SECOND_CLAP),
    "AHbh": ("A chance of bonus damage and a stun.", [("Chance", V("Hbh1", "%")), ("Bonus damage", V("Hbh3")), ("Stun", V("adur", " s"))]),
    "AHav": ("Giant form: armor, HP, damage and spell immunity.", [("Armor", ADD("Hav1")), ("HP", ADD("Hav2")), ("Damage", ADD("Hav3")), LASTS, MANA, CD]),
    "A005": _VAMPIRE,
    "A01K": ("Your base move speed is 400.", [], f"{_SECOND_BOLT}|n{_SECOND_CLAP}"),
    "A017": ("Toggle: burns enemies around you.", [("Damage", V("Eim1")), ("Every", V("adur", " s")), ("Mana per s", V("Eim2")), ("To start", V("amcs")), CD, RAD]),
    # Tauren Chieftain
    "AOsh": ("A wave of force: damage in a line.", [("Damage", V("Osh1")), ("Radius", V("aare")), ("Length", V("Osh3")), MANA, CD, RNG], _SECOND_WAVE),
    "AOws": (_STOMP[0], _STOMP[1], _SECOND_STOMP),
    "A00W": ("Attacks may shake the ground around the target.", [("Chance", V("War1", "%")), ("Damage", V("War2")), ("Full within", V("War3")), ("Half within", V("War4"))]),
    "A00E": ("Lightning hits every enemy around you.", [("Damage each", V("Efk1")), ("Cooldown", V("acdn", " s")), RAD, MANA]),
    "ACro": ("You deal more damage and gain armor.", [("Damage", PLUS("Roa1")), ("Armor", ADD("Roa2")), LASTS, MANA, CD]),
    "AOre": ("When you fall you rise again.", [("After", V("Ore1", " s")), CD]),
    "A03Q": ("You deal far more damage and gain armor.", [("Damage", PLUS("Roa1")), ("Armor", ADD("Roa2")), LASTS, MANA, CD],
             f"While on: Shockwave +{_strike('A04Q', 'Ucs1')} and War Stomp +{_strike('A01O', 'Ctc1')} strike again."),
    # Pit Lord
    "ANrf": ("Channel: waves of fire on an area, then a burn.", [("Waves", V("Hbz1")), ("Per wave", V("Hbz2")), ("Burn per s", V("Hbz5")), ("Max per wave", V("Hbz6")), RAD, MANA,
                                                                  ("Cooldown", V("acdn", " s")), ("Burn lasts", V("adur", " s")), RNG]),
    "AOw2": _STOMP,
    "ANca": ("Your attack also hits enemies around the target.", [("Splash", P("nca1")), RAD]),
    "ANdo": ("Marks a non-hero: damage every second until it dies, no spells for it. Doom Guards rise from it.",
             [("Damage per s", V("Ndo1")), ("Doom Guards", V("Ndo2")), ("They last", V("Ndo3", " s")), MANA, CD, RNG], "Monsters above level 5 refuse it."),
    "AUau": ("Allies near you move faster and heal.", [("Move speed", PLUS("Uau1")), ("HP per s", ADD("Uau2")), RAD]),
    "A02E": ("A howl: enemies around you deal less damage.", [("Less damage", P("Roa1")), LASTS, RAD, MANA, CD]),
    "A019": ("Instant: damage on one enemy.", [("Damage", V("Nfd3")), MANA, CD, RNG]),
    # Archmage
    "AHbz": ("Channel: waves of ice on an area.", [("Waves", V("Hbz1")), ("Per wave", V("Hbz2")), ("Max per wave", V("Hbz6")), RAD, MANA, ("Wave interval", V("acas", " s")), CD, RNG]),
    "AHwe": ("Summons water elementals to fight for you.", _SUMMON_ROWS),
    "A003": ("An ice shard: damage and a stun on one enemy.", [("Damage", V("Htb1")), MANA, ("Stun", V("adur", " s")), CD, RNG]),
    "AEsf": ("Channel: falling stars hit enemies around you.", [("Per hit", V("Esf1")), ("Every", V("Esf2", " s")), LASTS, RAD, MANA, CD]),
    "A00P": ("Enemies near you lose armor.", [("Armor", V("Had1")), RAD]),
    "ACam": ("A barrier stops spells on one unit.", [LASTS, MANA, CD, RNG]),
    "A02Y": ("Armor on one ally, melee attackers are chilled.", [("Armor", ADD("Ufa2")), ("Lasts", V("Ufa1", " s")), ("Chill", V("adur", " s")), MANA, CD, RNG]),
    # Lich
    "AUfn": ("Frost on one enemy and those around it, and a slow. The target takes both.", [("Target", V("Ufn2")), ("Nova", V("Ufn1")), RAD, ("Slow lasts", V("adur", " s")), MANA, CD, RNG]),
    "A04C": ("A cone of frost: damage, then a burn.", [("Damage", V("Ucs1")), ("Burn per s", V("Nbf5")), ("Length", V("Ucs3")), ("End radius", V("Ucs4")), ("Burn lasts", V("adur", " s")), MANA, CD]),
    "ANfa": ("Autocast: your attacks add damage and slow.", [("Damage", ADD("Hca1")), ("Slows move", P("Hca2")), ("Slows attack", P("Hca3")), LASTS, ("Mana a shot", V("amcs"))]),
    "A035": ("Summons frost beasts.", _SUMMON_ROWS),
    "AUfu": ("Autocast: armor on an ally, melee attackers are chilled.", [("Armor", ADD("Ufa2")), ("Lasts", V("Ufa1", " s")), MANA, ("Chill", V("adur", " s")), CD, RNG]),
    "A01L": ("A unit attacks faster but loses HP.", [("Attack speed", PLUS("Uhf1")), ("HP lost per s", V("Uhf2")), LASTS, MANA, CD, RNG]),
    "A006": _CHAOS,
    # Paladin
    "A00M": ("Heals a target, then jumps to other allies.", [("Heal each", V("Ocl1")), ("Targets in all", V("Ocl2")), MANA, CD, RNG]),
    "A00H": ("A howl: enemies around you deal less and lose armor.", [("Less damage", P("Roa1")), ("Armor", V("Roa2", pre="-")), LASTS, RAD, MANA, CD]),
    "A00A": ("Beams of light hit every enemy around you.", [("Damage each", V("Efk1")), RAD, MANA, CD]),
    "A00Y": ("Summons an invulnerable sphere of light.", [("Avg hit", UNIT_HIT()), ("Attacks every", UNIT_EVERY()), LASTS, MANA, CD]),
    "AHad": ("Allies near you gain armor.", [("Armor", ADD("Had1")), RAD]),
    "ANta": ("The closest enemies are forced to attack you.", [("Closest", V("Tau1")), RAD, CD]),
    "A010": ("One unit: faster, stronger, and its cooldowns reset.", [("Attack speed", V("Cri2", "%", "+", -100.0)), ("Damage", V("Cri3", "%", "+", -100.0)),
                                                                        ("Move speed", V("Cri1", "%", "+", -100.0)), LASTS, MANA, CD, RNG]),
    # Blademaster
    "AOwk": ("Invisible and faster. The hit that ends it deals bonus damage.", [LASTS, ("Move speed", PLUS("Owk2")), ("Bonus", V("Owk3")), MANA, CD]),
    "AOcr": _CRIT,
    "AOmi": ("Illusions of you, they deal less and take more. Removes magic from you.", [("Images", V("Omi1")), MANA, ("They deal", P("Omi2")), ("They take", V("Omi3", pre="x")), LASTS, CD]),
    "AOww": ("A storm of blades: damage around you, spell immune.", [("Damage per s", V("Oww1")), LASTS, RAD, MANA, CD]),
    "A045": ("Allies near you deal more with their attacks.", [("Damage", _drums), ("Radius", _drums_radius)]),
    "A04N": ("You attack and move faster, but take more damage.", [("Attack speed", PLUS("bsk2")), ("Move speed", PLUS("bsk1")), ("Damage taken", PLUS("bsk3")), LASTS, CD]),
    "A01F": ("You split into 3 warriors. If one lives to the end you return. If all fall, you die.", [("Warrior HP", UNIT_HP(_fixed("n00D"))), ("Avg hit", UNIT_HIT(_fixed("n00D"))), HERO_LASTS, MANA, CD]),
    # Beastmaster
    "ANsg": ("Summons bears.", _SUMMON_ROWS),
    "ACs7": ("Summons wolves.", [("Wolves", V("Osf2")), ("HP each", UNIT_HP()), ("Avg hit", UNIT_HIT()), LASTS, MANA, CD]),
    "ANsw": ("Summons hawks.", _SUMMON_ROWS),
    "Arsp": ("Channel: beasts run through an area and explode.", [("Beasts per s", V("Nst1")), ("Damage each", V("Nst3")), ("Blast radius", V("Nst4")), ("Area", V("aare")), LASTS, ("Range", V("aran")), MANA, CD]),
    "AEah": ("Allies near you: melee attackers take damage back.", [("Returned", P("Eah1")), RAD]),
    "A009": ("Summons a spirit pig.", _SUMMON_ROWS),
    "A02W": ("You become a Terror Wolf for a while.", [("Wolf HP", UNIT_HP(_fixed("n00M"))), ("Avg hit", UNIT_HIT(_fixed("n00M"))), HERO_LASTS, MANA, CD]),
    # Crypt Lord
    "AUim": ("Spikes in a line: damage, ground enemies thrown up.", [("Damage", V("Uim3")), ("Radius", V("aare")), ("In the air", V("Uim4", " s")), ("Stun", V("adur", " s")), ("Stun on heroes", V("ahdu", " s")),
                                                                      ("Length", V("Uim1")), MANA, CD, RNG]),
    "AUts": ("Armor, and melee attackers take damage back.", [("Armor", ADD("Uts3")), ("Returned", P("Uts1"))]),
    "AUcb": ("Autocast: raises a beetle from a corpse. It stays until killed.", [("HP each", UNIT_HP(_beetle)), ("Avg hit", UNIT_HIT(_beetle)), ("At most", V("Ucb5")), MANA, CD, RNG]),
    "AUls": ("Locusts bite enemies around you and bring you life.", [("Locusts", V("Uls1")), ("One every", V("Uls2", " s")), ("Max on one", V("Uls3")), ("Life back", P("Uls4")), RAD, LASTS, MANA, CD]),
    "A020": _POISON,
    "A024": ("You move and attack faster.", [("Move speed", PLUS("bsk1")), ("Attack speed", PLUS("bsk2")), LASTS, CD]),
    "A00Q": ("Channel: spikes hit ground enemies around you.", [("Per hit", V("Esf1")), ("Every", V("Esf2", " s")), LASTS, RAD, MANA, CD]),
    # Demon Hunter
    "AEim": ("Toggle: burns enemies around you.", [("Damage", V("Eim1")), ("Every", V("adur", " s")), ("Mana per s", V("Eim2")), RAD, ("To start", V("amcs"))]),
    "A00K": ("Negative energy: damage on one enemy.", [("Damage", V("Nfd3")), CD, RNG]),
    "AEev": _DODGE,
    "AEme": ("Demon form: a ranged attack and more HP.", [("HP", ADD("Eme5")), HERO_LASTS, MANA, CD]),
    "AUav": _VAMPIRE,
    "ACr1": ("Allies near you deal more damage.", [("Damage", PLUS("Roa1")), LASTS, RAD, MANA, CD]),
    "A02K": ("Negative spells last shorter on you, some do not work at all.", []),
    # Priestess of the Moon
    "AOcl": ("Lightning jumps between enemies, as strong on each.", [("Damage each", V("Ocl1")), ("Enemies in all", V("Ocl2")), CD, MANA, ("Jump radius", V("aare")), RNG]),
    "ANwm": ("Summons water minions.", _SUMMON_ROWS),
    "ANfl": ("A cone of lightning on enemies.", [("Damage each", V("Ocl1")), ("Enemies", V("Ocl2")), ("Length", V("Ucs3")), ("End radius", V("Ucs4")), MANA, CD, RNG]),
    "A01M": ("Channel: lightning strikes enemies in an area.", [("Per hit", V("Esf1")), ("Every", V("Esf2", " s")), LASTS, RAD, MANA, CD, RNG]),
    "AEar": _TRUESHOT,
    "ACrj": ("Heals one unit over time.", [("Heals", V("Rej1")), ("Over", V("adur", " s")), MANA, CD, RNG]),
    "A02U": _CHAOS,
}


def _spec(aid):
    entry = SPEC[aid]
    return entry[0], entry[1], entry[2] if len(entry) > 2 else ""


def _rows(aid, count):
    """(label, values) of the rows that change with the rank; a line of the ones that do not."""
    _what, rows, _after = _spec(aid)
    changing, constant = [], []
    for label, get in rows:
        values = [get(aid, r) for r in range(1, count + 1)]
        if len(set(values)) > 1:
            changing.append((label, values))
        elif values[0] not in ("0", "0 s", "0%", "+0", "+0%"):
            constant.append(f"{label} {values[0]}")
    return changing, ", ".join(constant) + "." if constant else ""


def _ranked(values, rank):
    """One row: the ranks side by side, coloured by where the champion stands. Rank 0 = no colours (the Learn card)."""
    if rank == 0:
        return " / ".join(values)
    parts = []
    for i, value in enumerate(values, start=1):
        colour = GOLD if i == rank else DONE if i < rank else GREY
        parts.append(f"{colour}{value}|r")
    return " / ".join(parts)


def title(aid, name, key, rank, count, grant=False):
    head = f"{GOLD}{name}|r [{GOLD}{key}|r] {BLUE}Rank {rank}/{count}|r"
    return f"{head} {BLUE}Hero level 20|r" if grant else head


def body(aid, rank, count, preview=""):
    what, _rows_spec, after = _spec(aid)
    changing, constant = _rows(aid, count)
    lines = [what]
    lines += [f"{label}: {_ranked(values, rank)}" for label, values in changing]
    if constant:
        lines.append(constant)
    if after:
        lines.append(after)
    if rank > 0:
        lines.append(f"{GREEN}Max rank|r" if rank == count else f"{ORANGE}Next: rank {rank + 1} at hero level {hero_level(aid, rank + 1)}|r")
    if preview:
        lines.append(f"{GREY}{preview}|r")
    return "|n".join(lines)


def learn_body(aid, count):
    needed = [str(hero_level(aid, r)) for r in range(1, count + 1)]
    return body(aid, 0, count) + f"|n{BLUE}Hero level:|r {' / '.join(needed)}"


def toggle_off(aid, name, key, rank, count):
    """The button while it is on (Immolation): that it runs and how to stop it, above the same overview."""
    return (f"Stop {GOLD}{name}|r [{GOLD}{key}|r] {BLUE}Rank {rank}/{count}|r", f"{GREEN}On.|r Press to stop.|n{body(aid, rank, count)}")


def ability_tips(aid, name, key, learnable, grant=False, preview=""):
    """[(field, level, text)]: every text of this ability, for each of its ranks."""
    count = levels(aid)
    out = []
    for rank in range(1, count + 1):
        out.append(("atp1", rank, title(aid, name, key, rank, count, grant)))
        out.append(("aub1", rank, body(aid, rank, count, preview)))
        if _table("Units_AbilityData.slk").get(_ability(aid)[0], {}).get("code") == "AEim":
            tip, text = toggle_off(aid, name, key, rank, count)
            out += [("aut1", rank, tip), ("auu1", rank, text)]
    if learnable:
        out.append(("aret", 0, f"Learn {GOLD}{name}|r [{GOLD}{key}|r] {BLUE}Rank %d/{count}|r"))
        out.append(("arut", 0, learn_body(aid, count)))
    return out


def drum_tips(rank, key):
    """The real aura of War Drums, one ability per rank: the same text as the rank it stands for."""
    count = levels("A045")
    return [("atp1", 1, title("A045", "War Drums", key, rank, count)), ("aub1", 1, body("A045", rank, count))]


def visible(text):
    """A text as the player reads it: without its colours."""
    out, i = [], 0
    while i < len(text):
        if text.startswith("|c", i):
            i += 10
        elif text.startswith("|r", i):
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def check(texts):
    """Every text fits the engine (too long crashes the map at load). Returns the lines that will wrap, for the build's log."""
    long_lines = []
    for owner, field, text in texts:
        if len(text.encode("utf-8")) > MAX_RAW:
            raise SystemExit(f"{owner} {field}: {len(text.encode('utf-8'))} bytes, the limit here is {MAX_RAW}")
        for line in visible(text).split("|n"):
            if field in ("aub1", "arut", "auu1") and len(line) > LINE_CHARS and " / " in line:
                long_lines.append((owner, line))
    return long_lines
