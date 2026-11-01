#!/usr/bin/env python3
"""Builds "TechTools Castle Defence" (WarCraft III TFT 1.27, 8 players, hero lane defense).

    python3 build.py            # dist/TechToolsCastleDefence.w3x + pjass + base-id check + install into the game
    python3 build.py --test     # dist/TechToolsCastleDefence_TEST.w3x (fast timers, scripted self-test)
    python3 build.py --no-install

Everything (terrain, walls, objects, script, art) is generated here; see CLAUDE.md and docs/.
"""
import math
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "gen"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import layout as LY                       # noqa: E402
import objects as OB                      # noqa: E402
import w3files as WF                      # noqa: E402
import hotkeys as HK                      # noqa: E402
import splash as SP                       # noqa: E402
import icons as IC                        # noqa: E402
from mpq import write_w3x, GameData       # noqa: E402

GAME_DIR = os.environ.get("WC3_DIR", "/home/novakj/games/warcraft3")
TEST = "--test" in sys.argv
# VERSION: bump it for every build that is published or shared (LAN players need the SAME file). It is in the
# map name (game list, lobby, loading screen), the file name and the catalogue title.
MAP_VERSION = "1.9"
MAP_FILE = "TechToolsCastleDefence_TEST.w3x" if TEST else f"TechToolsCastleDefence_v{MAP_VERSION}.w3x"
OLD_MAP_FILES = ["CastleDefense4Fronts.w3x"]          # removed from the game folder on install
MAP_NAME = f"TechTools Castle Defence v{MAP_VERSION}"
# coloured name for the game's map list / lobby / loading screen: TechTools blue + WarCraft gold + version
MAP_NAME_COLORED = f"|cff2e8bffTechTools|r |cffffcc00Castle Defence|r |cff4fc3ffv{MAP_VERSION}|r"
SEED = 1270

# Hidden developer cheats (-addmoney, -addwood/-addtree, -lvl) work only for these player names.
DEV_NAMES = ["root", "jiri_novak", "WorldEdit"]

# timings (seconds)
SELECT_TIME = float(os.environ.get("CD_SELECT", "8")) if TEST else 45.0
FIRST_WAVE_DELAY = 10.0 if TEST else 30.0
WAVE_INTERVAL = 10.0
WAVE_BREAK = 25.0 if TEST else 120.0     # shopping break after every 5th wave

W = LY.MAP_TILES                  # tiles per side
NPTS = W + 1                      # tilepoints per side
ORIGIN = -LY.HALF

GROUND = ["Kdrt", "Kdtr", "Kfst", "Ksmb", "Klgb", "Kdkt", "Ksqt", "Oaby", "Dlvc", "Idki", "Ibkb", "Kfsl"]
T = {name: i for i, name in enumerate(GROUND)}
CLIFFS = ["CKdi", "CKdt"]

VAR_CHOICES = list(range(18))     # WE's observed tile-variation distribution
VAR_WEIGHTS = [1170 if v % 4 == 0 else 135 if v % 4 == 1 else 55 if v % 4 == 2 else 13 for v in range(16)] + [1150, 1120]

# custom forces + FIXED player settings: the 4 invader computers sit in their own team, so the lobby
# always has an opponent ("You must have an opponent") and the host cannot remove them.
MAP_FLAGS = 0x8000 | 0x4000 | 0x1000 | 0x0800 | 0x0400 | 0x0040 | 0x0020 | 0x0010 | 0x0008   # = 0xdc78, as Legion TD etc.
PLAYER_COLORS = ["|cffff0303", "|cff0042ff", "|cff1ce6b9", "|cff540081",
                 "|cfffffc01", "|cfffe8a0e", "|cff20c000", "|cffe55bb0"]
FACTION_COLOR_IDX = [9, 10, 8, 11]
INVADER_RACE = [("RACE_PREF_UNDEAD", 3)] * 4          # all four enemy computers are Undead in the lobby

WALL_H, WALL_V = "ITw0", "ITw2"   # Icecrown stone walls: along x (10x2 cells) / along y (2x10 cells)
WALL_LEN = 320                    # one wall piece covers 320 units
CORNER_DOODAD = "LObz"            # glowing brazier on wall corners (doodad: no runtime pathing)
TORCH_DOODAD = "LOtz"             # glowing torch (no pathing) lighting the lanes


# ----------------------------------------------------------------------------- noise
def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def value_noise(x, y, scale, seed):
    fx, fy = x / scale, y / scale
    ix, iy = math.floor(fx), math.floor(fy)
    tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return (a + (b - a) * tx) + ((c + (d - c) * tx) - (a + (b - a) * tx)) * ty


# ----------------------------------------------------------------------------- terrain
def ground_texture(x, y, kind, idx):
    n = value_noise(x, y, 420.0, 23)
    if kind in ("boundary", "void"):
        return T["Oaby"]
    if kind == "plaza":
        r = max(abs(x), abs(y))
        if math.hypot(x, y) < 700:
            return T["Kdkt"]
        return T["Klgb"] if r < 1300 else T["Ksmb"]
    if kind == "grove":
        return T["Kfsl"] if n > 0.5 else T["Kfst"]
    if kind == "shared":                                  # gate levels 2-5 (idx 0-3)
        if idx == 1:                                      # Level 3, the Frozen Gate: ice
            return T["Idki"] if n > 0.45 else T["Ibkb"]
        if idx == 2:                                      # Level 4, the Shadow Gate: dark squares
            return T["Ksqt"] if n > 0.45 else T["Kdkt"]
        if idx == 3:                                      # Level 5, the Inferno Gate: scorched ground
            return T["Dlvc"] if n > 0.6 else T["Kdrt"]
        return T["Dlvc"] if n > 0.45 else T["Kdtr"]       # Level 2, the Dark Gate: violet ruins + dark trim
    if kind == "hall":
        hx, hy = LY.HALL_CENTRE
        return T["Kdkt"] if math.hypot(x - hx, y - hy) < 450 else T["Ksqt"]
    if kind == "base":
        if idx == 0:
            return T["Idki"] if n > 0.45 else T["Ibkb"]
        if idx == 1:
            return T["Dlvc"] if n > 0.35 else T["Kdtr"]
        if idx == 2:
            return T["Kfsl"] if n > 0.4 else T["Kdrt"]
        return T["Kdtr"] if n > 0.5 else T["Kdrt"]
    # lane
    if LY.road_distance(x, y) < 230:
        return T["Kfst"]
    return T["Kdtr"] if n > 0.55 else T["Kdrt"]


def build_terrain(rng):
    points = []
    A, B, C, D = LY.CAMCOMP
    for j in range(NPTS):
        y = ORIGIN + 128 * j
        for i in range(NPTS):
            x = ORIGIN + 128 * i
            kind, idx = LY.classify(x, y)
            boundary = i < A or i > NPTS - 1 - B or j < C or j > NPTS - 1 - D
            var = rng.choices(VAR_CHOICES, VAR_WEIGHTS)[0]
            points.append((0x2000, 0x2000, 0, ground_texture(x, y, kind, idx), var, 0, 2, boundary))
    return points


# ----------------------------------------------------------------------------- cells, walls, pathing
def cell_walk():
    """walk[j][i] for every 128x128 cell (region edges lie on the 128 grid)."""
    return [[LY.walkable(LY.classify(ORIGIN + 64 + 128 * i, ORIGIN + 64 + 128 * j)[0]) for i in range(W)]
            for j in range(W)]


def _place_run(out, horizontal, fixed, a0, a1, rng):
    """Wall pieces along a run [a0, a1] (world units) on the line `fixed`."""
    length = a1 - a0
    if length < 256:
        return False
    if length < WALL_LEN:
        c = round((a0 + a1) / 2 / 32.0) * 32.0
        x, y = (c, fixed) if horizontal else (fixed, c)
        out.append((WALL_H if horizontal else WALL_V, rng.randrange(5), x, y, 0.0, math.radians(270.0), 1.0, 100))
        return True
    n = int(math.ceil((length - WALL_LEN) / 256.0)) + 1
    for k in range(n):
        c = a0 + WALL_LEN / 2 + (0 if n == 1 else k * (length - WALL_LEN) / (n - 1))
        c = round(c / 32.0) * 32.0
        x, y = (c, fixed) if horizontal else (fixed, c)
        out.append((WALL_H if horizontal else WALL_V, rng.randrange(5), x, y, 0.0, math.radians(270.0), 1.0, 100))
    return True


def build_walls(walk, rng):
    """Walls on the void side of every edge between walkable cells and the abyss."""
    walls, deco = [], []
    # horizontal edges: between cell rows j and j+1, wall runs along x
    for j in range(W - 1):
        i = 0
        while i < W:
            a, b = walk[j][i], walk[j + 1][i]
            if a == b:
                i += 1
                continue
            void_above = a          # walkable below -> abyss above
            i0 = i
            while i < W and walk[j][i] != walk[j + 1][i] and walk[j][i] == a:
                i += 1
            edge_y = ORIGIN + 128 * (j + 1)
            fy = edge_y + 32 if void_above else edge_y - 32
            x0, x1 = ORIGIN + 128 * i0, ORIGIN + 128 * i
            _place_run(walls, True, fy, x0, x1, rng)
            # torches every ~700 units on the walkable side
            ty = edge_y - 56 if void_above else edge_y + 56
            n = int((x1 - x0) // 700)
            for k in range(n):
                tx = x0 + (k + 0.5) * (x1 - x0) / n
                deco.append((TORCH_DOODAD, 0, tx, ty, 0.0, math.radians(270.0), 1.0, 100))
    # vertical edges: between cell columns i and i+1, wall runs along y
    for i in range(W - 1):
        j = 0
        while j < W:
            a, b = walk[j][i], walk[j][i + 1]
            if a == b:
                j += 1
                continue
            void_right = a
            j0 = j
            while j < W and walk[j][i] != walk[j][i + 1] and walk[j][i] == a:
                j += 1
            edge_x = ORIGIN + 128 * (i + 1)
            fx = edge_x + 32 if void_right else edge_x - 32
            y0, y1 = ORIGIN + 128 * j0, ORIGIN + 128 * j
            _place_run(walls, False, fx, y0, y1, rng)
            tx = edge_x - 56 if void_right else edge_x + 56
            n = int((y1 - y0) // 700)
            for k in range(n):
                ty = y0 + (k + 0.5) * (y1 - y0) / n
                deco.append((TORCH_DOODAD, 0, tx, ty, 0.0, math.radians(270.0), 1.0, 100))
    # braziers on the corners of the walkable areas
    for j in range(1, W):
        for i in range(1, W):
            cells = [walk[j - 1][i - 1], walk[j - 1][i], walk[j][i - 1], walk[j][i]]
            cnt = sum(cells)
            if cnt in (1, 3):
                vx, vy = ORIGIN + 128 * i, ORIGIN + 128 * j
                # push the brazier into the abyss side of the corner
                ox = sum((-1 if k % 2 == 0 else 1) for k, c in enumerate(cells) if not c)
                oy = sum((-1 if k < 2 else 1) for k, c in enumerate(cells) if not c)
                ox = 0 if ox == 0 else (48 if ox > 0 else -48)
                oy = 0 if oy == 0 else (48 if oy > 0 else -48)
                deco.append((CORNER_DOODAD, 0, vx + ox, vy + oy, 0.0, math.radians(270.0), 1.0, 100))
    return walls, deco


def build_pathing(walk):
    """war3map.wpm: 4x4 pathing cells per tile. 0x40 open, 0x4A abyss (no walk/build, flyable), 0xCE boundary."""
    PW = W * 4
    grid = bytearray(PW * PW)
    for j in range(W):
        for i in range(W):
            kind = LY.classify(ORIGIN + 64 + 128 * i, ORIGIN + 64 + 128 * j)[0]
            v = 0xCE if kind == "boundary" else (0x40 if walk[j][i] else 0x4A)
            for dj in range(4):
                row = (j * 4 + dj) * PW + i * 4
                grid[row:row + 4] = bytes([v]) * 4
    return PW, grid


# ----------------------------------------------------------------------------- minimap
def minimap_xy(x, y):
    pw = LY.PLAY_MAXX - LY.PLAY_MINX
    ph = LY.PLAY_MAXY - LY.PLAY_MINY
    return (int((x - LY.PLAY_MINX) / pw * 256), int((LY.PLAY_MAXY - y) / ph * 256))


def build_minimap():
    from PIL import Image
    img = Image.new("RGB", (256, 256))
    px = img.load()
    pw = LY.PLAY_MAXX - LY.PLAY_MINX
    ph = LY.PLAY_MAXY - LY.PLAY_MINY
    base_col = {0: (90, 110, 150), 1: (120, 40, 30), 2: (40, 110, 110), 3: (110, 80, 50)}
    for py in range(256):
        y = LY.PLAY_MAXY - (py + 0.5) * ph / 256
        for pxl in range(256):
            x = LY.PLAY_MINX + (pxl + 0.5) * pw / 256
            kind, idx = LY.classify(x, y)
            if kind in ("boundary", "void"):
                n = value_noise(x, y, 500.0, 3)
                c = (6 + int(10 * n), 4, 14 + int(16 * n))
            elif kind == "plaza":
                c = (95, 90, 100)
            elif kind == "hall":
                c = (120, 100, 60)
            elif kind == "base":
                c = base_col[idx]
            elif kind == "shared":
                c = [(125, 30, 40), (60, 120, 170), (100, 50, 150), (190, 100, 30)][idx]
            else:
                c = (88, 72, 58) if LY.road_distance(x, y) < 230 else (60, 50, 44)
            px[pxl, py] = c
    return img


# ----------------------------------------------------------------------------- JASS
def jstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def jr(v):
    return f"{float(v):.1f}"


GLOBALS = """
globals
    // ---- generated data ----
    real array gWpX
    real array gWpY
    integer gWpCount = 0
    integer array gGateState
    string array gGateDir
    integer array gGateGold
    integer array gGateHpAbil
    integer array gGateDmgAbil
    integer array gGateTintR
    integer array gGateTintG
    integer array gGateTintB
    integer array gStageUnit
    integer gFrontBase = 4
    integer gBackDiv = 2
    integer gFrontMax = 30
    integer gBackMax = 15
    integer array gWaveChamp
    integer gChampEvery = 10
    integer array gIncome
    integer array gPremItem
    string array gPremName
    string array gPremEffect
    integer gPremCount = 0
    integer gPremMax = 5
    integer gPremPrice = 1000
    string array gDevName
    integer gDevCount = 0
    integer gAttrMaxHeroLevel = 110
    integer gAttrPerLevel = 3
    unit array gProtector
    real array gProtX
    real array gProtY
    integer gBankItem = 0
    integer array gEpicItem
    string array gEpicName
    integer gReachItem = 0
    integer array gPotItem
    integer array gPotHp
    integer array gPotMp
    integer gPotCount = 0
    integer gReachTech = 0
    integer gReachMax = 5
    integer gReachStep = 150
    unit gBankShop = null
    unit gArmoryShop = null
    integer gIncomeStep = 100
    real array gHeroX
    real array gHeroY
    integer array gGateType
    real array gGateX
    real array gGateY
    real array gGateFace
    real array gLaneMarkX
    real array gLaneMarkY
    real array gLaneLabelX
    real array gLaneLabelY
    integer array gTierUnit
    integer array gChampion
    integer array gBaseType
    integer array gTurretType
    integer array gBossType
    real array gNexusX
    real array gNexusY
    real array gTowerX
    real array gTowerY
    real array gTowerSpawnX
    real array gTowerSpawnY
    real array gNexusSpawnX
    real array gNexusSpawnY
    real array gDirFace
    string array gBossOrd1
    integer array gBossKind1
    string array gBossOrd2
    integer array gBossKind2
    integer array gBossSummon
    integer array gBossSummonCount
    string array gDirName
    string array gDirColor
    string array gFactionName
    integer array gFactionColorIdx
    string array gBaseName
    string array gTurretName
    string array gBossName
    string array gPlayerColorCode
    player array gInvader
    integer array gHeroPool
    integer gHeroPoolCount = 0
    integer gCastleType = 0
    integer gSoulType = 0
    integer gCircleType = 0
    integer array gStatItem
    integer array gStatNext
    integer array gBonusAbil
    string array gKindName
    integer array gKindValue
    integer gKinds = 8
    integer array gStocked
    integer array gCastleNext
    string array gKindEffect
    integer array gKindType
    integer gSoulTmp = 0
    integer array gHeroTavern
    real array gZoom
    boolean array gFollow
    rect array gCircleRect
    integer gGrabP = 0
    boolean gTickStarted = false
    dialog gEndDialog = null
    button gEndRestart = null
    button gEndQuit = null
    boolean gEndWon = false
    integer gStatTiers = 0
    integer gStatPerLevel = 2
    real gHallX = 0.0
    real gHallY = 0.0
    real gSelectTime = 45.0
    real gFirstWaveDelay = 30.0
    real gWaveInterval = 10.0
    real gWaveBreak = 120.0
    real array gShopFxX
    real array gShopFxY
    integer gShopFxCount = 0
    boolean gTestMode = false
    // ---- state ----
    integer gTestClock = 0
    integer gTestRound = 0
    player gKingdom = null
    integer gWave = 0
    integer gElapsed = 0
    integer gGameTime = 0
    integer gBossTier = 0
    boolean gStarted = false
    boolean gSelecting = false
    boolean gGameOver = false
    boolean gWaitingClear = false
    timer gWaveTimer = null
    timerdialog gWaveDialog = null
    timer gSelectTimer = null
    timerdialog gSelectDialog = null
    group gWaveUnits = null
    group gFirstWave = null
    integer array gFirstWaveLeft
    unit gCastle = null
    unit array gNexus
    unit array gTower
    unit array gBoss
    integer array gBossTick
    integer array gLaneState
    boolean array gLaneActive
    integer array gKills
    integer array gDeaths
    texttag array gPickTag
    integer array gBoardRow
    multiboard gBoard = null
    unit array gSoul
    unit array gLaneMarker
    destructable array gGate
    unit array gTavern
    unit array gHero
    boolean array gHeroTaken
    timer array gReviveTimer
    timerdialog array gReviveDialog
endglobals
"""

DESCRIPTION = ("Pick a champion and defend YOUR lane! Up to 8 players, each with his own lane, tower and Nexus. "
               "Waves grow every round; destroy your tower and Nexus, kill the boss, open the Dark Gate. "
               "Stats at your circle, castle upgrades for trees, secret grove with shops and a bank. "
               "Spells on Q W E R, -help for commands. A TechTools game.")

FRONT_NAMES = ["North", "North", "East", "East", "South", "South", "West", "West"]
SIDE_NAMES = ["left", "right"]


def build_script():
    L = []
    a = L.append
    a("//===========================================================================")
    a(f"// {MAP_NAME} v{MAP_VERSION} -- generated by build.py, do not edit by hand")
    a("//===========================================================================")
    a(GLOBALS)
    a("function InitData takes nothing returns nothing")
    a(f"    set gWpCount = {len(LY.LANE_WAYPOINTS_ARM)}")
    for lane in range(8):
        for k, (x, y) in enumerate(LY.lane_waypoints(lane)):
            a(f"    set gWpX[{lane * 8 + k}] = {jr(x)}")
            a(f"    set gWpY[{lane * 8 + k}] = {jr(y)}")
        hx, hy = LY.hero_spot(lane)
        a(f"    set gHeroX[{lane}] = {jr(hx)}")
        a(f"    set gHeroY[{lane}] = {jr(hy)}")
        a(f"    set gPlayerColorCode[{lane}] = {jstr(PLAYER_COLORS[lane])}")
        mx, my = LY.lane_marker(lane)
        a(f"    set gLaneMarkX[{lane}] = {jr(mx)}")
        a(f"    set gLaneMarkY[{lane}] = {jr(my)}")
        nx, ny = LY.nexus_pos(lane)
        a(f"    set gNexusX[{lane}] = {jr(nx)}")
        a(f"    set gNexusY[{lane}] = {jr(ny)}")
        tx, ty = LY.tower_pos(lane)
        a(f"    set gTowerX[{lane}] = {jr(tx)}")
        a(f"    set gTowerY[{lane}] = {jr(ty)}")
        sx, sy = LY.tower_spawn(lane)
        a(f"    set gTowerSpawnX[{lane}] = {jr(sx)}")
        a(f"    set gTowerSpawnY[{lane}] = {jr(sy)}")
        sx, sy = LY.nexus_spawn(lane)
        a(f"    set gNexusSpawnX[{lane}] = {jr(sx)}")
        a(f"    set gNexusSpawnY[{lane}] = {jr(sy)}")
        gid, gx, gy, gf = LY.lane_gate(lane)
        a(f"    set gGateType[{lane}] = '{gid}'")
        a(f"    set gGateX[{lane}] = {jr(gx)}")
        a(f"    set gGateY[{lane}] = {jr(gy)}")
        a(f"    set gGateFace[{lane}] = {jr(gf)}")
        lx, ly = LY.lane_label(lane)
        a(f"    set gLaneLabelX[{lane}] = {jr(lx)}")
        a(f"    set gLaneLabelY[{lane}] = {jr(ly)}")
    # shopping-break pings/effects: the grove entrance + every grove building
    fx = [LY.GROVE_ENTRANCE] + [(x, y) for (_, x, y) in LY.GROVE_BUILDINGS]
    for i, (x, y) in enumerate(fx):
        a(f"    set gShopFxX[{i}] = {jr(x)}")
        a(f"    set gShopFxY[{i}] = {jr(y)}")
    a(f"    set gShopFxCount = {len(fx)}")
    a(f"    set gAttrMaxHeroLevel = {OB.ATTR_REQ_LEVEL + OB.ATTR_LEVELS - 1}")
    a(f"    set gAttrPerLevel = {OB.ATTR_PER_LEVEL}")
    for i, n in enumerate(DEV_NAMES):
        a(f"    set gDevName[{i}] = {jstr(n)}")
    a(f"    set gDevCount = {len(DEV_NAMES)}")
    # upgradable premium items: gPremItem[i*8 + L] (L = 1..PREMIUM_LEVELS), Lv 1 = the shop item
    for i, (name, _b, _ic, _ab, _f, _v, effect) in enumerate(OB.PREMIUM_DEF):
        a(f"    set gPremName[{i}] = {jstr(name)}")
        for lv in range(1, OB.PREMIUM_LEVELS + 1):      # (not "L": that is the script's line list here)
            a(f"    set gPremItem[{i * 8 + lv}] = '{OB.premium_item_id(i, lv)}'")
            a(f"    set gPremEffect[{i * 8 + lv}] = {jstr(effect(lv))}")
    a(f"    set gPremCount = {len(OB.PREMIUM_DEF)}")
    a(f"    set gPremMax = {OB.PREMIUM_LEVELS}")
    a(f"    set gPremPrice = {OB.PREMIUM_PRICE}")
    for (lvl, iid, _aid, name, bonus, _icon) in OB.EPIC_ITEMS:
        a(f"    set gEpicItem[{lvl}] = '{iid}'")
        a(f"    set gEpicName[{lvl}] = {jstr(f'{name} (+{bonus} all stats)')}")
    a(f"    set gBankItem = '{OB.BANK_ITEM}'")
    a(f"    set gIncomeStep = {OB.INCOME_STEP}")
    a(f"    set gReachItem = '{OB.REACH_ITEM}'")
    a(f"    set gReachTech = '{OB.REACH_TECH}'")
    a(f"    set gReachMax = {OB.REACH_LEVELS}")
    a(f"    set gReachStep = {OB.REACH_STEP}")
    for i, (iid, _n, _e, _g, hp, mp, *_r) in enumerate(OB.POTIONS):
        a(f"    set gPotItem[{i}] = '{iid}'")
        a(f"    set gPotHp[{i}] = {hp}")
        a(f"    set gPotMp[{i}] = {mp}")
    a(f"    set gPotCount = {len(OB.POTIONS)}")
    # gate lanes 8-11 = Levels 2-5 (arms 4-7), all owned by the Scourge computer (Player 9)
    for g in OB.GATE_LEVELS:
        lane, arm, f = g["lane"], g["arm"], g
        wps, tower, nexus, tspawn, nspawn, gate = LY.GATE_GEOMETRY[lane]
        for k, (x, y) in enumerate(wps):
            a(f"    set gWpX[{lane * 8 + k}] = {jr(x)}")
            a(f"    set gWpY[{lane * 8 + k}] = {jr(y)}")
        for name, (x, y) in (("Tower", tower), ("Nexus", nexus), ("TowerSpawn", tspawn), ("NexusSpawn", nspawn)):
            a(f"    set g{name}X[{lane}] = {jr(x)}")
            a(f"    set g{name}Y[{lane}] = {jr(y)}")
        gid, gx, gy, gf = gate
        a(f"    set gGateType[{lane}] = '{gid}'")
        a(f"    set gGateX[{lane}] = {jr(gx)}")
        a(f"    set gGateY[{lane}] = {jr(gy)}")
        a(f"    set gGateFace[{lane}] = {jr(gf)}")
        a(f"    set gGateState[{lane}] = -1")
        a(f"    set gGateDir[{lane}] = {jstr(g['dir'])}")
        a(f"    set gGateGold[{lane}] = {g['gold']}")
        a(f"    set gGateHpAbil[{lane}] = '{OB.gate_hp_abil(lane)}'")
        a(f"    set gGateDmgAbil[{lane}] = {repr(OB.gate_dmg_abil(lane)) if g['unit_dmg'] else 0}")
        r_, g_, b_ = g["tint"]
        a(f"    set gGateTintR[{lane}] = {r_}")
        a(f"    set gGateTintG[{lane}] = {g_}")
        a(f"    set gGateTintB[{lane}] = {b_}")
        a(f"    set gInvader[{arm}] = Player(8)")
        a(f"    set gDirColor[{arm}] = {jstr(f['color'])}")
        a(f"    set gFactionName[{arm}] = {jstr(f['name'])}")
        a(f"    set gBaseName[{arm}] = {jstr(f['base'][1])}")
        a(f"    set gTurretName[{arm}] = {jstr(f['turret'][1])}")
        a(f"    set gDirFace[{arm}] = 270.0")
        a(f"    set gBaseType[{arm}] = '{OB.base_id(arm)}'")
        a(f"    set gTurretType[{arm}] = '{OB.turret_id(arm)}'")
        a(f"    set gChampion[{arm}] = '{f['champion']}'")
        # gate boss: own unit type, spells/summons copied from its source faction's boss
        src, bname = g["boss"][0], g["boss"][1]
        sb = OB.FACTIONS[src]["boss"]
        a(f"    set gBossType[{arm * 3 + 1}] = '{OB.boss_id(arm, 1)}'")
        a(f"    set gBossName[{arm}] = {jstr(bname)}")
        a(f"    set gBossOrd1[{arm}] = {jstr(sb['cast1'][0])}")
        a(f"    set gBossKind1[{arm}] = {sb['cast1'][1]}")
        a(f"    set gBossOrd2[{arm}] = {jstr(sb['cast2'][0])}")
        a(f"    set gBossKind2[{arm}] = {sb['cast2'][1]}")
        a(f"    set gBossSummon[{arm}] = '{sb['summon'][0]}'")
        a(f"    set gBossSummonCount[{arm}] = {sb['summon'][1] + g['level'] // 2}")
    # stage rosters: gStageUnit[arm*6 + stage*2 + 0 front / 1 back]; arm 4 = the Dark Gate
    for d, f in enumerate(OB.FACTIONS + OB.GATE_LEVELS):      # standardized copies (q<arm><stage><m|r>)
        for st in range(len(f["stages"])):
            a(f"    set gStageUnit[{d * 6 + st * 2}] = '{OB.wave_unit_id(d, st, False)}'")
            a(f"    set gStageUnit[{d * 6 + st * 2 + 1}] = '{OB.wave_unit_id(d, st, True)}'")
    a(f"    set gFrontBase = {OB.WAVE_FRONT_BASE}")
    a(f"    set gBackDiv = {OB.WAVE_BACK_DIV}")
    a(f"    set gFrontMax = {OB.WAVE_FRONT_MAX}")
    a(f"    set gBackMax = {OB.WAVE_BACK_MAX}")
    for d in range(4 + len(OB.GATE_LEVELS)):
        a(f"    set gWaveChamp[{d}] = '{OB.wave_champion_id(d)}'")
    a(f"    set gChampEvery = {OB.WAVE_CHAMP_EVERY}")
    for d, f in enumerate(OB.FACTIONS):
        a(f"    set gInvader[{d}] = Player({8 + d})")
        a(f"    set gDirName[{d}] = {jstr(LY.DIR_NAMES[d])}")
        a(f"    set gDirColor[{d}] = {jstr(f['color'])}")
        a(f"    set gFactionName[{d}] = {jstr(f['name'])}")
        a(f"    set gFactionColorIdx[{d}] = {FACTION_COLOR_IDX[d]}")
        a(f"    set gBaseName[{d}] = {jstr(f['base'][1])}")
        a(f"    set gTurretName[{d}] = {jstr(f['turret'][1])}")
        a(f"    set gBossName[{d}] = {jstr(f['boss']['name'])}")
        a(f"    set gDirFace[{d}] = {jr(LY.DIR_FACING_IN[d])}")
        a(f"    set gBaseType[{d}] = '{OB.base_id(d)}'")
        a(f"    set gTurretType[{d}] = '{OB.turret_id(d)}'")
        for k in range(3):
            a(f"    set gBossType[{d * 3 + k}] = '{OB.boss_id(d, k)}'")
        for t, (melee, ranged) in enumerate(f["tiers"]):
            a(f"    set gTierUnit[{d * 12 + t * 2}] = '{melee}'")
            a(f"    set gTierUnit[{d * 12 + t * 2 + 1}] = '{ranged}'")
        a(f"    set gChampion[{d}] = '{f['champion']}'")
        b = f["boss"]
        a(f"    set gBossOrd1[{d}] = {jstr(b['cast1'][0])}")
        a(f"    set gBossKind1[{d}] = {b['cast1'][1]}")
        a(f"    set gBossOrd2[{d}] = {jstr(b['cast2'][0])}")
        a(f"    set gBossKind2[{d}] = {b['cast2'][1]}")
        a(f"    set gBossSummon[{d}] = '{b['summon'][0]}'")
        a(f"    set gBossSummonCount[{d}] = {b['summon'][1]}")
    tav_of = {h: k for k, (_, _, hs) in enumerate(OB.TAVERNS) for h in hs}
    for i, h in enumerate(OB.ALL_HEROES):
        a(f"    set gHeroPool[{i}] = '{h}'")
        a(f"    set gHeroTavern[{i}] = {tav_of[h]}")
    a(f"    set gHeroPoolCount = {len(OB.ALL_HEROES)}")
    a(f"    set gCastleType = '{OB.CASTLE_ID}'")
    a(f"    set gSoulType = '{OB.SOUL_ID}'")
    a(f"    set gCircleType = '{OB.CIRCLE_ID}'")
    for si in range(OB.KINDS):
        a(f"    set gKindName[{si}] = {jstr(OB.kind_name(si))}")
        a(f"    set gKindValue[{si}] = {OB.kind_value(si)}")
        a(f"    set gKindEffect[{si}] = {jstr(OB.kind_effect(si))}")
        a(f"    set gKindType[{si}] = {OB.KIND_TYPE[OB.KINDS_DEF[si]['type']]}")
        for k in range(OB.kind_tiers(si)):
            a(f"    set gStatItem[{si * 64 + k}] = '{OB.stat_item_id(si, k)}'")
            if OB.KINDS_DEF[si]["type"] in ("abil", "castleabil"):
                a(f"    set gBonusAbil[{si * 64 + k}] = '{OB.bonus_abil_id(si, k)}'")
    a(f"    set gKinds = {OB.KINDS}")

    a(f"    set gStatTiers = {OB.STAT_TIERS}")
    a(f"    set gStatPerLevel = {OB.STAT_PER_LEVEL}")
    a(f"    set gHallX = {jr(LY.HALL_CENTRE[0])}")
    a(f"    set gHallY = {jr(LY.HALL_CENTRE[1])}")
    a(f"    set gSelectTime = {jr(SELECT_TIME)}")
    a(f"    set gFirstWaveDelay = {jr(FIRST_WAVE_DELAY)}")
    a(f"    set gWaveInterval = {jr(WAVE_INTERVAL)}")
    a(f"    set gWaveBreak = {jr(WAVE_BREAK)}")
    a(f"    set gTestMode = {'true' if TEST else 'false'}")
    a("endfunction")
    a("")
    a("function CreateNeutrals takes nothing returns nothing")
    a("    local player p = Player(PLAYER_NEUTRAL_PASSIVE)")
    for (kind, x, y) in LY.GROVE_BUILDINGS:
        uid = OB.SHOPS[kind][0] if kind in OB.SHOPS else kind
        if kind == "bank":
            a(f"    set gBankShop = CreateUnit(p, '{uid}', {jr(x)}, {jr(y)}, 270.0)")
        elif kind == "armory":
            a(f"    set gArmoryShop = CreateUnit(p, '{uid}', {jr(x)}, {jr(y)}, 270.0)")
        else:
            a(f"    call CreateUnit(p, '{uid}', {jr(x)}, {jr(y)}, 270.0)")
    for k, ((tid, _, _), (dx, dy)) in enumerate(zip(OB.TAVERNS, LY.HALL_TAVERNS)):
        x, y = LY.hall_point(dx, dy)
        a(f"    set gTavern[{k}] = CreateUnit(p, '{tid}', {jr(x)}, {jr(y)}, 270.0)")
    a("    set p = null")
    a("endfunction")
    a("")
    with open(os.path.join(ROOT, "gen", "castle_logic.j"), encoding="utf-8") as fh:
        a(fh.read())
    a("function InitCustomPlayerSlots takes nothing returns nothing")
    for i in range(8):
        a(f"    call SetPlayerStartLocation(Player({i}), {i})")
        a(f"    call ForcePlayerStartLocation(Player({i}), {i})")
        a(f"    call SetPlayerColor(Player({i}), ConvertPlayerColor({i}))")
        a(f"    call SetPlayerRacePreference(Player({i}), RACE_PREF_HUMAN)")
        a(f"    call SetPlayerRaceSelectable(Player({i}), false)")   # no race choice: your race is your champion
        a(f"    call SetPlayerController(Player({i}), MAP_CONTROL_USER)")
    for d in range(4):
        i = 8 + d
        a(f"    call SetPlayerStartLocation(Player({i}), {i})")
        a(f"    call ForcePlayerStartLocation(Player({i}), {i})")
        a(f"    call SetPlayerColor(Player({i}), ConvertPlayerColor({FACTION_COLOR_IDX[d]}))")
        a(f"    call SetPlayerRacePreference(Player({i}), {INVADER_RACE[d][0]})")
        a(f"    call SetPlayerRaceSelectable(Player({i}), false)")
        a(f"    call SetPlayerController(Player({i}), MAP_CONTROL_COMPUTER)")
    a("endfunction")
    a("")
    a("function InitCustomTeams takes nothing returns nothing")
    for i in range(8):
        a(f"    call SetPlayerTeam(Player({i}), 0)")
        a(f"    call SetPlayerState(Player({i}), PLAYER_STATE_ALLIED_VICTORY, 1)")
    for i in range(8):
        for j in range(8):
            if i != j:
                a(f"    call SetPlayerAllianceStateAllyBJ(Player({i}), Player({j}), true)")
                a(f"    call SetPlayerAllianceStateVisionBJ(Player({i}), Player({j}), true)")
    for i in range(8, 12):
        a(f"    call SetPlayerTeam(Player({i}), 1)")
        a(f"    call SetPlayerState(Player({i}), PLAYER_STATE_ALLIED_VICTORY, 1)")
        for j in range(8, 12):
            if i != j:
                a(f"    call SetPlayerAllianceStateAllyBJ(Player({i}), Player({j}), true)")
    a("endfunction")
    a("")
    a("function InitAllyPriorities takes nothing returns nothing")
    for i in range(8):
        a(f"    call SetStartLocPrioCount({i}, 1)")
        a(f"    call SetStartLocPrio({i}, 0, {i ^ 1}, MAP_LOC_PRIO_HIGH)")
    for i in range(8, 12):
        a(f"    call SetStartLocPrioCount({i}, 0)")
    a("endfunction")
    a("")
    a("function main takes nothing returns nothing")
    a(f"    call SetCameraBounds({jr(LY.PLAY_MINX)} + GetCameraMargin(CAMERA_MARGIN_LEFT), {jr(LY.PLAY_MINY)} + GetCameraMargin(CAMERA_MARGIN_BOTTOM), "
      f"{jr(LY.PLAY_MAXX)} - GetCameraMargin(CAMERA_MARGIN_RIGHT), {jr(LY.PLAY_MAXY)} - GetCameraMargin(CAMERA_MARGIN_TOP), "
      f"{jr(LY.PLAY_MINX)} + GetCameraMargin(CAMERA_MARGIN_LEFT), {jr(LY.PLAY_MAXY)} - GetCameraMargin(CAMERA_MARGIN_TOP), "
      f"{jr(LY.PLAY_MAXX)} - GetCameraMargin(CAMERA_MARGIN_RIGHT), {jr(LY.PLAY_MINY)} + GetCameraMargin(CAMERA_MARGIN_BOTTOM))")
    a('    call SetDayNightModels("Environment\\\\DNC\\\\DNCLordaeron\\\\DNCLordaeronTerrain\\\\DNCLordaeronTerrain.mdl", "Environment\\\\DNC\\\\DNCLordaeron\\\\DNCLordaeronUnit\\\\DNCLordaeronUnit.mdl")')
    a('    call NewSoundEnvironment("Default")')
    a('    call SetAmbientDaySound("BlackCitadelDay")')
    a('    call SetAmbientNightSound("BlackCitadelNight")')
    a('    call SetMapMusic("Music", true, 0)')
    a("    call InitBlizzard()")
    a("    call InitGame()")
    a("endfunction")
    a("")
    a("function config takes nothing returns nothing")
    a(f"    call SetMapName({jstr(MAP_NAME_COLORED)})")
    a(f"    call SetMapDescription({jstr(DESCRIPTION)})")
    a("    call SetPlayers(12)")
    a("    call SetTeams(12)")
    a("    call SetGamePlacement(MAP_PLACEMENT_TEAMS_TOGETHER)")
    for i in range(8):
        x, y = LY.hero_spot(i)
        a(f"    call DefineStartLocation({i}, {jr(x)}, {jr(y)})")
    for d in range(4):
        x, y = LY.nexus_pos(2 * d)
        a(f"    call DefineStartLocation({8 + d}, {jr(x)}, {jr(y)})")
    a("    call InitCustomPlayerSlots()")
    a("    call InitCustomTeams()")
    a("    call InitAllyPriorities()")
    a("endfunction")
    a("")
    return "\r\n".join(L).replace("\r\n", "\n").replace("\n", "\r\n")


# ----------------------------------------------------------------------------- w3i / mmp
def build_w3i():
    players = []
    for i in range(8):
        x, y = LY.hero_spot(i)
        players.append({"num": i, "type": 1, "race": 1, "fixed": 1,
                        "name": f"{FRONT_NAMES[i]} ({SIDE_NAMES[i % 2]} lane)", "x": float(x), "y": float(y)})
    for d, f in enumerate(OB.FACTIONS):
        x, y = LY.nexus_pos(2 * d)
        players.append({"num": 8 + d, "type": 2, "race": INVADER_RACE[d][1], "fixed": 1,
                        "name": f["name"], "x": float(x), "y": float(y)})
    mL, mB, mR, mT = 512, 256, 512, 256      # GetCameraMargin values (from the official maps)
    cb = [LY.PLAY_MINX + mL, LY.PLAY_MINY + mB, LY.PLAY_MAXX - mR, LY.PLAY_MAXY - mT,
          LY.PLAY_MINX + mL, LY.PLAY_MAXY - mT, LY.PLAY_MAXX - mR, LY.PLAY_MINY + mB]
    A, B, C, D = LY.CAMCOMP
    info = {
        "saves": 2, "editor": 6052, "name": MAP_NAME_COLORED, "author": "Jiri Novak (generated with Claude)",
        "description": DESCRIPTION, "players_rec": "1-8 (one champion per lane)",
        "camera_bounds": [float(v) for v in cb], "camcomp": list(LY.CAMCOMP),
        "play_w": W - A - B, "play_h": W - C - D, "flags": MAP_FLAGS, "tileset": "K",
        "ls_title": MAP_NAME_COLORED, "ls_subtitle": "Pick a champion. Hold your lane. Break the Nexus.",
        "ls_text": DESCRIPTION,
        "players": players,
        "forces": [{"flags": 0x0B, "mask": 0x0FF, "name": "Defenders of Lordaeron"},
                   {"flags": 0x03, "mask": 0xF00, "name": "Invaders"}],
    }
    return WF.write_w3i(info)


def build_mmp():
    icons = [(2,) + minimap_xy(*LY.hero_spot(i)) for i in range(8)]

    return WF.write_mmp(icons)


# ----------------------------------------------------------------------------- main
def pjass(script_path):
    exe = os.path.join(ROOT, "tools", "pjass-src", "pjass")
    if not os.path.exists(exe):
        print("WARNING: pjass not built, skipping syntax check")
        return
    r = subprocess.run([exe, os.path.join(ROOT, "ref", "Scripts_common.j"),
                        os.path.join(ROOT, "ref", "Scripts_Blizzard.j"), script_path],
                       capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        sys.exit("pjass failed")


def misc_constants(game):
    """war3mapMisc.txt = the game's full [Misc] gameplay constants (Units\\MiscGame.txt) with our edits.
    The whole section is written, like the World Editor does, so nothing falls back to 0."""
    lines = game.read("Units\\MiscGame.txt").decode("latin1").splitlines()
    edits = {"MaxHeroLevel": str(OB.MAX_HERO_LEVEL)}
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        out.append(f"{key}={edits[key]}" if key in edits else line)
    return ("\r\n".join(out) + "\r\n").encode("latin1")


REQUIRED_SCRIPT_DATA = ["set gBankItem = ", "set gIncomeStep = ", "set gPremItem[1] = ", "set gPremCount = ",
                        "set gShopFxCount = ", "set gDevCount = ", "set gAttrPerLevel = ", "set gReachItem = ",
                        "set gGateState[11] = ", "set gStageUnit[0] = ", "set gEpicItem[5] = ", "set gStatItem[0] = ", "set gHeroPool[0] = ",
                        "set gPotCount = "]


def check_script_data(script):
    """Fail the build if a data block vanished from InitData. An edit once deleted the Bank / premium / dev-name
    data: the map still compiled and ran, but Bank buys and item upgrades silently did nothing (2026-10-31)."""
    missing = [s for s in REQUIRED_SCRIPT_DATA if s not in script]
    if missing:
        sys.exit("InitData is missing: " + ", ".join(missing))


def check_object_bases():
    """Every custom object must be based on a REAL object of its kind. An item based on an ability id built fine
    and then crashed the game right after the loading screen (2026-10-31), so this fails the build instead."""
    from slk import read_slk
    ref = os.path.join(ROOT, "ref")
    known = {"unit": set(read_slk(os.path.join(ref, "Units_UnitData.slk"))),
             "item": set(read_slk(os.path.join(ref, "Units_ItemData.slk"))),
             "ability": set(read_slk(os.path.join(ref, "Units_AbilityData.slk")))}
    bad = []
    for kind, objs in (("unit", OB.custom_units()), ("item", OB.custom_items()), ("ability", OB.custom_abilities())):
        for base, new, _mods in objs:
            if base not in known[kind]:
                bad.append(f"{kind} {new} based on unknown {kind} '{base}'")
    if bad:
        sys.exit("bad object bases:\n  " + "\n  ".join(bad[:20]))


def main():
    install = "--no-install" not in sys.argv and not TEST
    rng = random.Random(SEED)
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)

    points = build_terrain(rng)
    w3e = WF.write_w3e("K", GROUND, CLIFFS, NPTS, NPTS, float(ORIGIN), float(ORIGIN), points)
    walk = cell_walk()
    walls, deco = build_walls(walk, rng)
    pw, path = build_pathing(walk)
    print(f"{len(walls)} wall pieces, {len(deco)} torches/braziers")
    script = build_script()
    script_path = os.path.join(ROOT, "dist", "war3map.j")
    with open(script_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(script)
    pjass(script_path)
    check_script_data(script)
    check_object_bases()

    art = SP.render()
    files = {
        "war3map.j": script.encode("utf-8"),
        "war3map.w3i": build_w3i(),
        "war3map.w3e": w3e,
        "war3map.wpm": WF.write_wpm(pw, pw, path),
        "war3map.shd": bytes(pw * pw),
        "war3map.doo": WF.write_doo(walls + deco),
        "war3map.mmp": build_mmp(),
        "war3mapMap.blp": WF.write_blp_paletted(build_minimap()),
        "war3map.w3u": WF.write_w3u(OB.custom_units(), OB.original_unit_mods()),
        "war3map.w3t": WF.write_w3u(OB.custom_items(), OB.original_item_mods()),
        "war3map.w3a": WF.write_w3a(OB.original_ability_mods() + HK.hero_hotkey_mods(os.path.join(ROOT, "ref"), OB.ALL_HEROES),
                                    OB.custom_abilities()),
        "war3map.w3q": WF.write_w3a([], OB.custom_upgrades()),
        "war3mapPreview.tga": SP.preview_tga(art),
    }
    for path, tile in SP.loading_tiles(art).items():          # TechTools loading screen
        files[path] = WF.write_blp_paletted(tile, dither=True, mips=False)
    game = GameData(GAME_DIR)
    files.update(IC.stat_icons(game))                          # Str / Agi / Int shop icons
    files["war3mapMisc.txt"] = misc_constants(game)            # gameplay constants: hero max level
    out = os.path.join(ROOT, "dist", MAP_FILE)
    # header 'max players' = HUMAN slots only (Legion TD: 8 humans + 2 computers -> 8). Writing 12 here
    # made the lobby treat the 4 invader computers as open, editable slots.
    write_w3x(out, files, MAP_NAME_COLORED, MAP_FLAGS, 8)
    print(f"wrote {out} ({os.path.getsize(out) // 1024} KiB)")
    if install:
        dest_dir = os.path.join(GAME_DIR, "Maps", "CustomMaps")
        os.makedirs(dest_dir, exist_ok=True)
        # ATOMIC replace: copy to a temp name, then rename over the old map. A running game keeps reading
        # its already-open (old) file. Copying over it in place made a running game crash with
        # "Not enough memory - SFile.cpp line 898" (2026-10-31).
        dest = os.path.join(dest_dir, MAP_FILE)
        tmp = dest + ".tmp"
        shutil.copy2(out, tmp)
        os.replace(tmp, dest)
        # older builds of THIS map (other versions / the unversioned name) go away, so the list shows one version
        olds = OLD_MAP_FILES + [f for f in os.listdir(dest_dir)
                                if f.startswith("TechToolsCastleDefence") and f.endswith(".w3x") and f != MAP_FILE]
        for old in olds:
            if os.path.exists(os.path.join(dest_dir, old)):
                os.remove(os.path.join(dest_dir, old))
                print(f"removed old {old}")
        print(f"installed -> {os.path.join(dest_dir, MAP_FILE)}")


if __name__ == "__main__":
    main()
