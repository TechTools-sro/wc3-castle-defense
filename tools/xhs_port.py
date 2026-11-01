#!/usr/bin/env python3
"""The 12 champions of X Hero Siege 3.28, as data: gen/xhs_data.py is generated from the local reference map, read-only.

    tools/xhs_port.py write   read the reference and write gen/xhs_data.py (numbers, art paths, no text, no map file)
    tools/xhs_port.py check   the repo's gen/xhs_data.py against the reference, exit 1 on any difference
    tools/xhs_port.py show ID one object as the reference has it (with its text), for reading

The reference is the owner's local copy (REFERENCE, checked by SHA-256) and stays out of this public repo. Only numbers and
paths of the game's own art are copied; every text a player reads is our own (gen/xhs_text.py).
"""
import hashlib
import json
import os
import pprint
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mpq import Archive      # noqa: E402

REFERENCE = "/home/novakj/games/warcraft3/Maps/CustomMaps/X Hero Siege 3.28.w3x"
REFERENCE_SHA = "6a9f7076ec64a91fc616f1af35f2f325b70ca316e2f2bdca70fc1bd6e774ec5b"
OUT = os.path.join(os.path.dirname(HERE), "gen", "xhs_data.py")

# The 12 of Jiří's "best 12", chosen with the release coordinator. Q W E R T = the reference's five skills; R is its ultimate (2 levels).
ROSTER = [
    ("H007", ["A028", "A02A", "A000", "A029", "AOae"]),      # Dryad: Evasion, Multiple Arrows, Critical Arrows, Trueshot, Endurance
    ("Hmkg", ["AHtb", "AHtc", "AHbh", "AHav", "A005"]),      # Mountain King
    ("Otch", ["AOsh", "AOws", "A00W", "A00E", "AOae"]),      # Tauren Chieftain
    ("Nplh", ["ANrf", "AOw2", "ANca", "ANdo", "AUau"]),      # Pit Lord
    ("Hamg", ["AHbz", "AHwe", "A003", "AEsf", "A00P"]),      # Archmage
    ("Ulic", ["AUfn", "A04C", "ANfa", "A035", "AUfu"]),      # Lich
    ("Hpal", ["A00M", "A00H", "A00A", "A00Y", "AHad"]),      # Paladin
    ("Obla", ["AOwk", "AOcr", "AOmi", "AOww", "A045"]),      # Blademaster
    ("Nbst", ["ANsg", "ACs7", "ANsw", "Arsp", "AEah"]),      # Beastmaster
    ("Ucrl", ["AUim", "AUts", "AUcb", "AUls", "A020"]),      # Crypt Lord
    ("Edem", ["AEim", "A00K", "AEev", "AEme", "AUav"]),      # Demon Hunter (the reference lists the aura first)
    ("Emoo", ["AOcl", "ANwm", "ANfl", "A01M", "AEar"]),      # Priestess of the Moon
]
# Trig_Level20Abilities: what a hero gets at level 20. (add, remove, permanent)
LEVEL20 = {
    "H007": (["A027"], [], False),
    "Hmkg": (["A017"], [], True),
    "Otch": (["AOre", "A03Q"], ["ACro"], True),
    "Nplh": (["A019"], [], False),
    "Hamg": (["A02Y"], [], False),
    "Ulic": (["A006"], [], False),
    "Hpal": (["A010"], [], False),
    "Obla": (["A01F"], [], False),
    "Nbst": (["A02W"], [], False),
    "Ucrl": (["A00Q"], [], False),
    "Edem": (["A02K"], [], True),
    "Emoo": (["A02U"], [], False),
}
# Added and removed by the reference's triggers, so nothing in the object data names them.
SCRIPTED = ["A04P", "A02V", "A01O", "A04Q", "A033", "A046", "A047", "A048"]
EXTRA_UNITS = ["Edmm"]       # the Demon Hunter's demon form
# The reference's id for a thing we keep under the same name, where our map already had another.
TEXT_U = {"utip", "utub", "ides", "unsf"}
TEXT_A = {"aub1", "arut", "atp1", "aret", "aut1", "auu1", "ansf", "anam"}
TEXT_B = {"ftip", "fube", "fnam", "fnsf"}
# Ours for every hero and skill: hotkeys, buttons, tavern position.
LAYOUT_A = {"ahky", "arhk", "auhk"}
LAYOUT_U = {"uhot", "ubpx", "ubpy", "ugol", "ulum", "ufoo", "usst", "usma", "usrg", "ureq", "ubuy"}


class Reader:
    def __init__(self, data):
        self.data, self.at = data, 0

    def i32(self):
        value = struct.unpack_from("<i", self.data, self.at)[0]
        self.at += 4
        return value

    def f32(self):
        value = struct.unpack_from("<f", self.data, self.at)[0]
        self.at += 4
        return round(value, 5)

    def rawcode(self):
        value = self.data[self.at:self.at + 4].decode("latin1")
        self.at += 4
        return value

    def text(self):
        end = self.data.index(b"\0", self.at)
        value = self.data[self.at:end].decode("utf-8", "replace")
        self.at = end + 1
        return value


def parse_object_file(data, levels):
    """{id: {'base': id, 'custom': bool, 'mods': [(field, type, level, pointer, value)]}}. Types: 0 int, 1 real, 2 unreal, 3 string."""
    r = Reader(data)
    r.i32()
    out = {}
    for custom in (False, True):
        for _ in range(r.i32()):
            base, new = r.rawcode(), r.rawcode()
            mods = []
            for _m in range(r.i32()):
                field, kind = r.rawcode(), r.i32()
                level = pointer = 0
                if levels:
                    level, pointer = r.i32(), r.i32()
                value = r.i32() if kind == 0 else r.f32() if kind in (1, 2) else r.text()
                r.rawcode()
                mods.append((field, kind, level, pointer, value))
            out[new if custom else base] = {"base": base, "custom": custom, "mods": mods}
    return out


def load_reference():
    with open(REFERENCE, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    if digest != REFERENCE_SHA:
        sys.exit(f"the reference is not the expected file: {digest}")
    archive = Archive(REFERENCE)
    return {"units": parse_object_file(archive.read("war3map.w3u"), False), "abils": parse_object_file(archive.read("war3map.w3a"), True),
            "buffs": parse_object_file(archive.read("war3map.w3h"), False)}


def tokens(value):
    return [t for t in re.split(r"[,\s]+", value) if len(t) == 4] if isinstance(value, str) else []


class GameTables:
    """The game's own default tables (ref/, local, never published): what an object inherits when the map does not override it."""

    def __init__(self):
        from slk import read_slk
        root = os.path.join(os.path.dirname(HERE), "ref")
        self.ability = read_slk(os.path.join(root, "Units_AbilityData.slk"))
        self.ability_meta = read_slk(os.path.join(root, "Units_AbilityMetaData.slk"))
        self.unit_abilities = read_slk(os.path.join(root, "Units_UnitAbilities.slk"))
        self.unit_data = read_slk(os.path.join(root, "Units_UnitData.slk"))
        self.buffs = set()

    def ability_column(self, field):
        """The default-table column of an ability field: Hwe1 -> UnitID, Eme1 -> DataA, abuf -> BuffID ..."""
        meta = self.ability_meta.get(field)
        if not meta:
            return None
        name = meta.get("field", "")
        data = meta.get("data", "")
        if name == "Data" and data not in ("", "0", None):
            return "Data" + "ABCDEFGHI"[int(data) - 1]
        return name or None


REFERENCE_COLUMNS = ["UnitID", "BuffID", "EfctID"] + ["Data" + c for c in "ABCDEFGHI"]


def ability_edges(item, ref, game):
    """Every object an ability really names at every level: the map's value where it sets one, else the inherited default.
    An override replaces the default, so a reference it replaced is not followed (A01Q's burrow forms)."""
    obj = ref["abils"].get(item)
    base = obj["base"] if obj else item
    row = game.ability.get(base, {})
    levels = int(row.get("levels") or 1)
    override = {}
    for (field, _k, level, _p, value) in (obj["mods"] if obj else []):
        if field == "alev":
            levels = int(value)
        column = game.ability_column(field)
        if column in REFERENCE_COLUMNS:
            override[(column, level)] = value
    edges = []
    for level in range(1, max(levels, 1) + 1):
        for column in REFERENCE_COLUMNS:
            value = override[(column, level)] if (column, level) in override else row.get(f"{column}{level}", "")
            edges += tokens(value)
    return edges


def unit_edges(item, ref, game):
    """The abilities a unit really has: the map's list where it sets one, else the inherited default."""
    obj = ref["units"].get(item)
    base = obj["base"] if obj else item
    row = game.unit_abilities.get(base, {})
    mods = {m[0]: m[4] for m in (obj["mods"] if obj else [])}
    edges = []
    for field, column in (("uabi", "abilList"), ("uhab", "heroAbilList")):
        value = mods[field] if field in mods else row.get(column, "")
        edges += tokens(value)
    return edges


def closure(ref):
    """Everything the 12 need, followed through effective fields: what the map overrides and what it inherits from the game.
    A native object the map does not change is walked too (Abu2 -> ucsB) but needs no copy."""
    game = GameTables()
    todo = [h for h, _ in ROSTER] + EXTRA_UNITS + [a for _, skills in ROSTER for a in skills] + SCRIPTED
    for add, remove, _ in LEVEL20.values():
        todo += add + remove
    seen = {"units": set(), "abils": set(), "buffs": set()}
    walked, unknown = set(), set()
    while todo:
        item = todo.pop()
        if item in walked:
            continue
        walked.add(item)
        if item in ref["buffs"]:
            seen["buffs"].add(item)
        elif item in ref["abils"] or item in game.ability:
            if item in ref["abils"]:
                seen["abils"].add(item)
            todo += ability_edges(item, ref, game)
        elif item in ref["units"] or item in game.unit_data:
            if item in ref["units"]:
                seen["units"].add(item)
            todo += unit_edges(item, ref, game)
        else:
            unknown.add(item)
    return seen, {u for u in unknown if not re.fullmatch(r"[0-9.,%-]+", u) and u.lower() not in ("none", "self")}


def public_mods(mods, drop):
    return [m for m in mods if m[0] not in drop]


def data_module(ref, seen):
    units = {k: (ref["units"][k]["base"], ref["units"][k]["custom"], public_mods(ref["units"][k]["mods"], TEXT_U | LAYOUT_U)) for k in sorted(seen["units"])}
    abils = {k: (ref["abils"][k]["base"], ref["abils"][k]["custom"], public_mods(ref["abils"][k]["mods"], TEXT_A | LAYOUT_A)) for k in sorted(seen["abils"])}
    buffs = {k: (ref["buffs"][k]["base"], ref["buffs"][k]["custom"], public_mods(ref["buffs"][k]["mods"], TEXT_B)) for k in sorted(seen["buffs"])}
    return {"ROSTER": ROSTER, "LEVEL20": LEVEL20, "SCRIPTED": SCRIPTED, "UNITS": units, "ABILS": abils, "BUFFS": buffs}


def render(module):
    head = ('"""Generated by tools/xhs_port.py from X Hero Siege 3.28 (' + REFERENCE_SHA[:16] + '...): numbers and paths of the game\'s own art, no text.\n'
            "Do not edit: change the tool. Mods are (field, type, level, pointer, value); types 0 int, 1 real, 2 unreal, 3 string.\"\"\"\n")
    body = "".join(f"{name} = {pprint.pformat(value, width=170, compact=True, sort_dicts=True)}\n" for name, value in module.items())
    return head + body


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    ref = load_reference()
    if command == "show":
        for item in sys.argv[2:]:
            for kind in ("units", "abils", "buffs"):
                if item in ref[kind]:
                    print(kind, item, "base", ref[kind][item]["base"], "custom", ref[kind][item]["custom"])
                    for mod in ref[kind][item]["mods"]:
                        print("  ", mod)
        return 0
    seen, missing = closure(ref)
    text = render(data_module(ref, seen))
    if command == "write":
        with open(OUT, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {OUT}: {len(seen['units'])} units, {len(seen['abils'])} abilities, {len(seen['buffs'])} buffs; named but not in the reference's tables: {sorted(missing)}")
        return 0
    if command == "check":
        with open(OUT, encoding="utf-8") as fh:
            same = fh.read() == text
        print("gen/xhs_data.py matches the reference" if same else "gen/xhs_data.py DIFFERS from the reference")
        return 0 if same else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
