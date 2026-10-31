"""Q W E R hotkeys for every champion's abilities (cast + learn), written as war3map.w3a edits.

Field ids from Units\\AbilityMetaData.slk (1.27): ahky Hotkey, arhk Researchhotkey, auhk Unhotkey,
abpx/abpy Buttonpos, arpx/arpy Researchbuttonpos, aubx/auby UnButtonpos, atp1 Tip (per level),
aret Researchtip. The old hotkey letter is highlighted inside the tooltip text (e.g. "Holy |cffffcc00L|right"),
so the highlight is removed and a "[Q]" tag is put in front instead.
"""
import csv
import glob
import os
import re

from w3files import VT_INT as I, VT_STRING as S
from slk import read_slk, read_profile

KEYS = "QWER"
_HILITE = re.compile(r"\|c[fF]{2}[fF]{2}[cC]{2}00(.)\|r")


def _profiles(ref):
    prof = {}
    for f in glob.glob(os.path.join(ref, "Units_*Ability*.txt")):
        for k, v in read_profile(f).items():
            prof.setdefault(k, {}).update(v)
    return prof


def _split(raw):
    if raw is None:
        return []
    raw = raw.strip()
    if '"' in raw:
        return next(csv.reader([raw]))
    return raw.split(",")          # unquoted per-level lists are plain comma-separated


def _retag(text, key):
    return f"|cffffcc00[{key}]|r " + _HILITE.sub(r"\1", text).strip()


def hero_hotkey_mods(ref, heroes):
    ua = read_slk(os.path.join(ref, "Units_UnitAbilities.slk"))
    ad = read_slk(os.path.join(ref, "Units_AbilityData.slk"))
    prof = _profiles(ref)
    out = {}
    for h in heroes:
        abils = [a for a in ua[h].get("heroAbilList", "").split(",") if a and a != "_"]
        for i, aid in enumerate(abils[:4]):
            key = KEYS[i]
            p = prof.get(aid, {})
            levels = int(ad.get(aid, {}).get("levels", "1") or 1)
            mods = [("ahky", S, 0, 0, key), ("arhk", S, 0, 0, key),
                    ("abpx", I, 0, 0, i), ("abpy", I, 0, 0, 2),
                    ("arpx", I, 0, 0, i), ("arpy", I, 0, 0, 0)]
            if p.get("Unhotkey"):
                mods += [("auhk", S, 0, 0, key), ("aubx", I, 0, 0, i), ("auby", I, 0, 0, 2)]
            tips = _split(p.get("Tip"))
            for lvl in range(1, levels + 1):
                if tips:
                    mods.append(("atp1", S, lvl, 0, _retag(tips[min(lvl, len(tips)) - 1], key)))
            rt = _split(p.get("Researchtip"))
            if rt:
                mods.append(("aret", S, 0, 0, _retag(rt[0], key)))
            out[aid] = mods
    return list(out.items())
