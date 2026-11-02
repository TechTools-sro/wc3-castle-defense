#!/usr/bin/env python3
"""Builds "TechTools Castle Defence" (WarCraft III TFT 1.27, 8 players, hero lane defense).

    python3 build.py            # dist/TechToolsCastleDefence.w3x + pjass + base-id check + install into the game
    python3 build.py --test     # dist/TechToolsCastleDefence_TEST.w3x (fast timers, scripted self-test)
    python3 build.py --no-install
    CD_PROBE='{...}' python3 build.py --probe   # dist/TechToolsCastleDefence_PROBE.w3x: production game + gen/probe.j (docs/balance.md)

Everything (terrain, walls, objects, script, art) is generated here; see CLAUDE.md and docs/.
"""
import math
import json
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
import xhs_data as XHS                    # noqa: E402
import w3files as WF                      # noqa: E402
import splash as SP                       # noqa: E402
import icons as IC                        # noqa: E402
from mpq import write_w3x, GameData       # noqa: E402

GAME_DIR = os.environ.get("WC3_DIR", "/home/novakj/games/warcraft3")
# A plain run installs into the owner's game, so anything unknown (--help) must stop here.
if set(sys.argv[1:]) - {"--test", "--no-install", "--probe"}:
    sys.exit("usage: build.py [--test] [--no-install] [--probe]   (no option = build and INSTALL into the game)")
TEST = "--test" in sys.argv
PROBE = json.loads(os.environ.get("CD_PROBE", "{}")) if "--probe" in sys.argv else None     # never installed, see apply_probe
if TEST and PROBE is not None:
    sys.exit("--probe and --test cannot be combined: --test changes the timers and runs TestStep")
# VERSION: bump it for every build that is published or shared (LAN players need the SAME file). It is in the
# map name (game list, lobby, loading screen), the file name and the catalogue title.
MAP_VERSION = "4.5"
MAP_FILE = "TechToolsCastleDefence_TEST.w3x" if TEST else "TechToolsCastleDefence_PROBE.w3x" if PROBE is not None else f"TechToolsCastleDefence_v{MAP_VERSION}.w3x"
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
WAVE_INTERVAL = 0.0                      # v3.5 (Jiri): the next wave comes right away once a wave is dead
WAVE_BREAK = 25.0 if TEST else 60.0      # shopping break after every BREAK_EVERY-th wave
BREAK_EVERY = 10
FINAL_DELAY = 3.0 if TEST else 30.0      # warning before the final boss rises

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
        if math.hypot(x, y) < 1050:
            return T["Kdkt"]
        return T["Klgb"] if r < 1950 else T["Ksmb"]
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
        return T["Kdkt"] if math.hypot(x - hx, y - hy) < 300 else T["Ksqt"]
    if kind == "base":
        if idx == 0:
            return T["Idki"] if n > 0.45 else T["Ibkb"]
        if idx == 1:
            return T["Dlvc"] if n > 0.35 else T["Kdtr"]
        if idx == 2:
            return T["Kfsl"] if n > 0.4 else T["Kdrt"]
        return T["Kdtr"] if n > 0.5 else T["Kdrt"]
    # lane
    if LY.road_distance(x, y) < 460:
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
                c = (88, 72, 58) if LY.road_distance(x, y) < 460 else (60, 50, 44)
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
    real gWaveHpGrowth = 0.0
    real gWaveDmgGrowth = 0.0
    real gGateHpPer = 0.0
    real gGateDmgPer = 0.0
    real gTeamHpPer = 0.0
    real array gRoleHp
    real array gRoleDmg
    real array gStageHp
    real array gStageDmg
    integer array gScaleBit
    integer gScaleHpBits = 0
    integer gScaleDmgBits = 0
    integer gScaleHpStep = 1
    integer gScaleDmgStep = 1
    integer array gScaleList
    integer array gScaleN
    integer gTeamCount = 1
    integer gSpawnLane = 0
    integer array gIncomeBudget
    integer gIncomeWaveSeconds = 120
    integer array gIncomeClock
    unit gTestLast = null
    unit gTestPreLeft = null
    integer array gGateTintR
    integer array gGateTintG
    integer array gGateTintB
    integer array gStageUnit
    integer gFrontBase = 4
    integer gBackPer = 1
    integer gFrontPer = 2
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
    integer array gPotToken
    integer array gPotPrice
    integer array gHeroSkill
    integer gSkillsPerHero = 5
    integer array gGrantHero
    integer array gGrantAbil
    integer array gGrantDrop
    boolean array gGrantPerm
    integer gGrantN = 0
    integer gGrantLevel = 20
    integer gDemonHero = 'Edem'
    integer gDemonForm = 'Edmm'
    integer array gDrumAura
    integer gOrderClap = 852096
    integer gOrderStomp = 852127
    integer gOrderCreepClap = 852253
    integer gOrderCreepBolt = 852252
    integer gOrderCreepSwarm = 852218
    integer array gCastHero
    integer array gCastAbil
    string array gCastName
    string array gCastOrder
    integer array gCastTarget
    integer array gCastEffect
    integer array gCastUnit
    integer array gCastCount
    real array gCastArea
    integer gCastN = 0
    unit gFinalBoss = null
    boolean gFinalPhase = false
    timer gFinalTimer = CreateTimer()
    timerdialog gFinalDialog = null
    integer gFinalType = 0
    string gFinalName = ""
    string gFinalFx = ""
    integer array gFinalBit
    integer array gFinalSpell
    integer gFinalTier = -1
    integer gFinalMinute = -1
    integer gFinalTick = 0
    integer gFinalShown = 0
    integer gFinalHpUnit = 0
    integer gFinalHpBase = 0
    integer gFinalHpPerMin = 0
    integer gFinalHpBits = 10
    integer gFinalHpStep = 100000
    integer gFinalDmgBase = 0
    integer gFinalDmgPerMin = 0
    integer gFinalDmgBits = 10
    integer gFinalDmgStep = 100
    integer gFinalArmorBits = 7
    integer gFinalArmorEvery = 2
    integer gFinalTiers = 10
    integer gFinalTierEvery = 5
    real gFinalX = 0.0
    real gFinalY = 0.0
    real gFinalLeash = 1700.0
    real gFinalDelay = 30.0
    integer gTestStunRemoved = 0
    integer gTestFinalCasts = 0
    integer gTestFinalTier = 0
    integer gTestFinalWave = 0
    integer gTestKillLane = 0
    integer gTestLanesT = 0
    integer gTestW0 = 0
    integer gTestTrees = 0
    integer gTestGateWave = 0
    unit gTestSentinel = null
    hashtable gTestHT = null
    trigger gTestHitTrig = null
    trigger gTestSpellTrig = null
    timer gTestClockT = null
    unit array gTestH
    unit array gTestFoe
    unit array gTestFriend
    unit gTestScene = null
    unit array gTestSceneFoe
    integer gTestC = 0
    integer gTestN = 0
    integer gTestRow = 0
    integer gTestRows = 0
    integer array gTestRowOf
    integer gTestHeroT = 0
    integer gTestCardT = 0
    integer gTestSoldType = 0
    integer gTestWardenStep = 0
    boolean gTestWardenStarted = false
    boolean gTestWardenDone = false
    real gTestWardenAt = 0.0
    real gTestWardenLife = 0.0
    integer gTestWardenItems = 0
    unit gTestWardenDummy = null
    unit gTestWardenBolt = null
    timer gTestPremClock = CreateTimer()
    timer gTestPremTimer = CreateTimer()
    integer gTestPremT = 0
    boolean gTestPremStarted = false
    boolean gTestPremDone = false
    boolean gTestPremAttackOff = false
    unit gTestPremHero = null
    unit array gTestPremFoe
    trigger gTestPremTrig = null
    trigger gTestPremTrig2 = null
    trigger gTestPremTrig3 = null
    integer gTestPremHits = 0
    real gTestPremDamage = 0.0
    real gTestPremHeal = 0.0
    real gTestPremLife = 0.0
    real gTestPremFirst = 0.0
    real gTestPremLast = 0.0
    real gTestPremBase = 0.0
    real gTestPremBase2 = 0.0
    real gTestPremX = 0.0
    real gTestPremY = 0.0
    real gTestPremX2 = 0.0
    integer gTestPremStuns = 0
    integer gTestBoltTries = 0
    integer gTestBoltT = 0
    integer gTestBuyT = 0
    integer gTestBuyStep = 0
    integer gTestBuyLumber = 0
    integer gTestBuyGold = 0
    integer gTestBuyIncome = 0
    integer gTestBuyStat = 0
    real gTestBuyMaxHp = 0.0
    boolean gTestBuyOrder = false
    rect gTestBuyRect = null
    integer gTestBoltSpells = 0
    integer gTestBoltHits = 0
    integer gTestBoltStunned = 0
    timer gTestBoltTimer = CreateTimer()
    real gTestBoltLife = 0.0
    integer gTestLearnStep = 0
    boolean gTestLearnStarted = false
    boolean gTestLearnDone = false
    item gTestPremItem = null
    timer gTestStunTimer = CreateTimer()
    integer gTestStunRuns = 0
    real gTestStunShortest = 0.0
    real gTestStunNow = 0.0
    integer gTestGearT = 0
    boolean gTestGearStarted = false
    boolean gTestGearDone = false
    real gTestGearPlain = 0.0
    real gTestGearBolt = 0.0
    integer gTestGearBoltHits = 0
    real gTestGearEvery = 0.0
    real gTestPremVolleyMin = 0.0
    real gTestPremVolleyAt = 0.0
    integer gTestPremVolleyId = 0
    integer gTestPremVolleyN = 0
    integer gTestPremVolleyBest = 0
    integer array gTestPremFoeVolley
    integer gTestPremPoison = 0
    integer gTestPremAttacked = 0
    integer gTestPremHurt = 0
    real array gTestPremD
    real array gBossBaseHp
    string gTestOnly = ""
    integer gTourN = 0
    integer gTestTourN = 0
    integer gTestTourStep = 0
    unit gTestTourHero = null
    integer array gTourKind
    integer array gTourHero
    integer array gTourLevel
    integer array gTourRank
    integer array gTourItem
    integer array gTourX
    integer array gTourY
    string array gTourOrder
    string array gTourName
    integer gTestPickBuy = 0
    integer gTestPickC = 0
    integer gTestPickStep = 0
    boolean gTestPickStarted = false
    boolean gTestPicksDone = false
    unit gTestPickOld = null
    boolean gTestCardDue = false
    trigger gTestDoomTrig = null
    integer gTestDoomStep = 0
    boolean gTestDoomStarted = false
    boolean gTestDoomDone = false
    boolean gTestDoomOrder = false
    integer gTestDoomSpell = 0
    unit gTestDoomHero = null
    unit gTestDoomFoe = null
    real gTestDoomLife = 0.0
    real gTestWeapon = 0.0
    integer gTestBossT = 0
    unit gTestBossHero = null
    real gTestBossX = 0.0
    real gTestBossY = 0.0
    real gTestBossLife = 0.0
    integer gTestBossSummons = 0
    boolean gTestBossDone = false
    integer gTestFormT = 0
    integer gTestFormFirst = 0
    integer gTestFormLast = 11
    boolean array gTestFormStill
    integer gTestFormStage = 0
    boolean gTestFormDone = false
    integer gTestDeathsSplit = 0
    integer gTestSceneControl = 0
    real array gTestFormStartX
    real array gTestFormStartY
    real gTestSceneEvery = 0.0
    boolean gTestScenePoison = false
    integer gTestBountyCalls = 0
    integer gTestRegenKind = 11
    integer gTestRegenT = 0
    real gTestRegenLife = 0.0
    unit gTestEnemyFound = null
    real array gTestFormAX
    real array gTestFormAY
    real array gTestFormFX
    real array gTestFormFY
    real array gTestFormStart
    real gDirSign0 = 1.0
    unit array gTestFormU
    integer array gTestFormRole
    integer array gTestFormLane
    integer gTestFormN = 0
    integer gChampMax = 6
    integer gTestSceneT = 0
    integer gTestTaurenT = 0
    integer gTestSplitT = 0
    boolean gTestSceneDone = false
    boolean gTestTaurenDone = false
    boolean gTestSplitDone = false
    boolean gTestDhChecked = false
    integer gTestDhMorphT = 0
    real gTestDhLife = 0.0
    integer gTestStatBefore = 0
    integer gTestDeathsBefore = 0
    real array gTestLifeBefore
    real array gTestFriendBefore
    integer array gTestOthersBefore
    integer array gTestCountBefore
    real array gTestManaBefore
    boolean array gTestOrderOk
    real array gTestHitT
    unit array gTestHitU
    real array gTestHitD
    integer gTestHitN = 0
    real gTestArrowMin = 150.0
    integer gTestBurstMost = 0
    integer gTestBurstFewest = 0
    integer gTestBurstDistinct = 0
    real gTestBurstEvery = 0.0
    real gTestBurstSpread = 0.0
    real gTestBurstDmgLow = 0.0
    real gTestBurstDmgHigh = 0.0
    real gTestFinalCastle = 0.0
    integer array gTestFinalCast
    real gTestFinalHp = 0.0
    real gTestFinalLife = 0.0
    integer gReachTech = 0
    integer gReachMax = 5
    integer gReachStep = 150
    integer gReachPrice = 1500
    unit gBankShop = null
    unit gArmoryShop = null
    unit gApoShop = null
    item array gPendItem
    integer array gPendP
    integer gPendN = 0
    integer gIncomeStep = 100
    real array gHeroX
    real array gHeroY
    integer array gGateType
    real array gGateX
    real array gGateY
    real array gGateFace
    real array gGateX2
    real array gGateY2
    destructable array gGate2
    real gFormX = 0.0
    real gFormY = 0.0
    real gFormFX = 0.0
    real gFormFY = -1.0
    real gFormForward = 0.0
    real gFormSide = 0.0
    integer gFormRow = 12
    real gFormStep = 96.0
    real gFormGap = 64.0
    integer gFormChampRow = 8
    real gFormChampStep = 160.0
    real array gLaneMarkX
    real array gLaneMarkY
    real array gLaneLabelX
    real array gLaneLabelY
    integer array gTierUnit
    integer array gChampion
    integer array gBaseType
    integer array gTurretType
    integer array gBossType
    integer array gGearHeart
    integer array gGearHands
    integer array gGearPlate
    real array gWardenAvgDmg
    real gWardenLeash = 1500.0
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
    integer array gBossSpell
    real array gBossAvgDmg
    real gBossHpGrowth = 0.0
    real gBossHpMax = 16.0
    real gBossDmgMax = 8.0
    trigger gTestSummonTrig = null
    unit array gTestSumU
    integer array gTestSumC
    integer gTestSumN = 0
    integer array gTestSumFrom
    integer gTestPalT = 0
    integer gTestPalCount = 0
    boolean gTestPalDone = false
    integer gTestLichT = 0
    boolean gTestLichDone = false
    boolean gTestLichSeen = false
    boolean gTestDhRoar = false
    unit gTestDhFresh = null
    unit gTestLichHero = null
    unit gTestLichFoe = null
    integer array gStunShown
    integer array gStunImpale
    real gBossDmgGrowth = 0.0
    integer gBossSpellLevels = 10
    integer gBossEvery1 = 7
    integer gBossEvery2 = 11
    integer gBossEverySummon = 25
    real gBossLeash = 1600.0
    boolean array gBossDue1
    boolean array gBossDue2
    boolean array gBossDue3
    integer array gBossBusy
    integer array gStunBuff
    integer gStunN = 0
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
    integer gBuyerType = 0
    integer gCircleType = 0
    integer array gStatItem
    integer array gStatNext
    integer array gStatApplied
    integer array gXpPending
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
    integer gKindStride = 128
    integer gStatPerLevel = 2
    real gHallX = 0.0
    real gHallY = 0.0
    real gHallSoulDY = -128.0
    real gCastleShopRange = 0.0
    real gBuyerX = 0.0
    real gBuyerY = 0.0
    real gSelectTime = 45.0
    real gFirstWaveDelay = 30.0
    real gWaveInterval = 0.0
    real gWaveBreak = 60.0
    integer gBreakEvery = 10
    real array gShopFxX
    real array gShopFxY
    integer gShopFxCount = 0
    boolean gTestMode = false
    // ---- state ----
    integer gTestClock = 0
    integer gTestRound = 0
    string array gTestLog
    integer gTestLogN = 0
    integer gTestLvl = 0
    integer gTestNext = 0
    boolean gTestHold = false
    integer gTestEdgeT = 0
    integer gTestGold = 0
    integer gTestKills = 0
    integer gTestSpawned = 0
    boolean gTestDeadOrder = false
    player gKingdom = null
    integer array gLaneWave
    integer array gLaneAlive
    boolean array gLaneWaiting
    timer array gLaneTimer
    timerdialog array gLaneDialog
    integer gElapsed = 0
    integer gGameTime = 0
    integer gBossTier = 0
    boolean gStarted = false
    boolean gSelecting = false
    boolean gGameOver = false
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
    integer gBoardRows = 1
    multiboard gBoard = null
    unit array gSoul
    unit array gBuyer
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
               "Spells on Q W E R T, innate D, level 20 F, -help for commands. A TechTools game.")

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
        (gid, gx, gy, gf), (_g2, gx2, gy2, _f2) = LY.lane_gate(lane)
        a(f"    set gGateX2[{lane}] = {jr(gx2)}")
        a(f"    set gGateY2[{lane}] = {jr(gy2)}")
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
    a(f"    set gAttrMaxHeroLevel = {OB.ATTR_AUTO_ABOVE}")
    a(f"    set gAttrPerLevel = {OB.ATTR_PER_LEVEL}")
    for i, n in enumerate(DEV_NAMES):
        a(f"    set gDevName[{i}] = {jstr(n)}")
    a(f"    set gDevCount = {len(DEV_NAMES)}")
    # upgradable premium items: gPremItem[i*8 + L] (L = 1..PREMIUM_LEVELS), Lv 1 = the shop item
    for i, (name, _b, _ic, _ab, _f, _v, _what, _rows) in enumerate(OB.PREMIUM_DEF):
        a(f"    set gPremName[{i}] = {jstr(name)}")
        for lv in range(1, OB.PREMIUM_LEVELS + 1):      # (not "L": that is the script's line list here)
            a(f"    set gPremItem[{i * 8 + lv}] = '{OB.premium_item_id(i, lv)}'")
            a(f"    set gPremEffect[{i * 8 + lv}] = {jstr(OB.premium_effect(i, lv))}")
    a(f"    set gPremCount = {len(OB.PREMIUM_DEF)}")
    for tier in (0, 1):
        for li in range(1 + len(OB.GATE_LEVELS)):
            a(f"    set gGearHeart[{li * 2 + tier}] = '{OB.gear_heart_id(li, tier)}'")
        a(f"    set gGearHands[{tier}] = '{OB.gear_hands_id(tier)}'")
        a(f"    set gGearPlate[{tier}] = '{OB.gear_plate_id(tier)}'")
    a(f"    set gWardenLeash = {jr(OB.WARDEN_LEASH)}")
    for tier in (0, 1):
        for li in range(1 + len(OB.GATE_LEVELS)):
            a(f"    set gBossBaseHp[{li * 2 + tier}] = {OB.boss_base_hp(li, tier) + OB.gear_heart_bonus(li, tier)}.0")
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
    a(f"    set gReachPrice = {OB.REACH_PRICE}")
    for i, (iid, _n, _e, gold, hp, mp, *_r) in enumerate(OB.POTIONS):
        a(f"    set gPotItem[{i}] = '{iid}'")
        a(f"    set gPotToken[{i}] = '{OB.POTION_TOKENS[i]}'")
        a(f"    set gPotPrice[{i}] = {gold}")
        a(f"    set gPotHp[{i}] = {hp}")
        a(f"    set gPotMp[{i}] = {mp}")
    a(f"    set gPotCount = {len(OB.POTIONS)}")
    # the champions: their five skills and what the script needs of them (HeroGrants, OnHeroGlue*)
    for c, h in enumerate(OB.ALL_HEROES):
        for s, aid in enumerate(OB.HERO_SKILLS[h]):
            a(f"    set gHeroSkill[{c * OB.SKILLS_PER_HERO + s}] = '{aid}'")
    a(f"    set gSkillsPerHero = {OB.SKILLS_PER_HERO}")
    k = 0
    for h, (add, remove, permanent) in XHS.LEVEL20.items():
        for i, aid in enumerate(add):
            a(f"    set gGrantHero[{k}] = '{h}'")
            a(f"    set gGrantAbil[{k}] = '{aid}'")
            a(f"    set gGrantDrop[{k}] = {chr(39) + remove[0] + chr(39) if remove and i == 0 else 0}")
            a(f"    set gGrantPerm[{k}] = {'true' if permanent else 'false'}")
            k += 1
    a(f"    set gGrantN = {k}")
    for level, aid in enumerate(("A033", "A046", "A047", "A048"), start=1):
        a(f"    set gDrumAura[{level}] = '{aid}'")
    if TEST or PROBE is not None:
        build_cast_table(a)
    if TEST and os.environ.get("CD_TEST_ONLY") == "tour":
        build_tour_table(a)
    if TEST and os.environ.get("CD_TEST_ONLY") == "finalbolt":
        a('    set gTestOnly = "finalbolt"')
    if TEST and os.environ.get("CD_TEST_ONLY") == "deadbuy":
        a('    set gTestOnly = "deadbuy"')
        x, y = card_point(0, 0)    # the first button of the castle's and the armory's card
        a(f"    set gTourX[0] = {x}")
        a(f"    set gTourY[0] = {y}")
    a(f"    set gFinalType = '{OB.FINAL_BOSS_ID}'")
    a(f"    set gFinalName = {jstr(OB.FINAL_BOSS_NAME)}")
    a(f"    set gFinalFx = {jstr(OB.FX['final'])}")
    for i, aid in enumerate(OB.final_bit_ids()):
        a(f"    set gFinalBit[{i}] = '{aid}'")
    for t in range(OB.FINAL_TIERS):
        for s, prefix in enumerate(OB.FINAL_SPELL_PREFIX):
            a(f"    set gFinalSpell[{t * 4 + s}] = '{prefix}{t}'")
    a(f"    set gFinalHpUnit = {OB.FINAL_HP_UNIT}")
    a(f"    set gFinalHpBase = {OB.FINAL_HP_BASE}")
    a(f"    set gFinalHpPerMin = {OB.FINAL_HP_PER_MIN}")
    a(f"    set gFinalHpBits = {OB.FINAL_HP_BITS}")
    a(f"    set gFinalHpStep = {OB.FINAL_HP_STEP}")
    a(f"    set gFinalDmgBase = {OB.FINAL_DMG_BASE}")
    a(f"    set gFinalDmgPerMin = {OB.FINAL_DMG_PER_MIN}")
    a(f"    set gFinalDmgBits = {OB.FINAL_DMG_BITS}")
    a(f"    set gFinalDmgStep = {OB.FINAL_DMG_STEP}")
    a(f"    set gFinalArmorBits = {OB.FINAL_ARMOR_BITS}")
    a(f"    set gFinalArmorEvery = {OB.FINAL_ARMOR_EVERY}")
    a(f"    set gFinalTiers = {OB.FINAL_TIERS}")
    a(f"    set gFinalTierEvery = {OB.FINAL_TIER_EVERY}")
    a(f"    set gFinalX = {jr(LY.FINAL_BOSS_POS[0])}")
    a(f"    set gFinalY = {jr(LY.FINAL_BOSS_POS[1])}")
    a(f"    set gFinalLeash = {jr(LY.FINAL_LEASH)}")
    a(f"    set gFinalDelay = {jr(FINAL_DELAY)}")
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
        (gid, gx, gy, gf), (_g2, gx2, gy2, _f2) = gate
        a(f"    set gGateX2[{lane}] = {jr(gx2)}")
        a(f"    set gGateY2[{lane}] = {jr(gy2)}")
        a(f"    set gGateType[{lane}] = '{gid}'")
        a(f"    set gGateX[{lane}] = {jr(gx)}")
        a(f"    set gGateY[{lane}] = {jr(gy)}")
        a(f"    set gGateFace[{lane}] = {jr(gf)}")
        a(f"    set gGateState[{lane}] = -1")
        a(f"    set gGateDir[{lane}] = {jstr(g['dir'])}")
        a(f"    set gGateGold[{lane}] = {g['gold']}")
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
        a(f"    set gBossType[{arm * 3}] = '{OB.boss_id(arm, 0)}'")
        a(f"    set gBossName[{arm}] = {jstr(bname)}")
        a(f"    set gBossOrd1[{arm}] = {jstr(sb['cast1'][0])}")
        a(f"    set gBossKind1[{arm}] = {sb['cast1'][1]}")
        a(f"    set gBossOrd2[{arm}] = {jstr(sb['cast2'][0])}")
        a(f"    set gBossKind2[{arm}] = {sb['cast2'][1]}")
        a(f"    set gBossSummon[{arm}] = '{sb['summon'][0]}'")
        a(f"    set gBossSummonCount[{arm}] = {sb['summon'][1] + g['level'] // 2}")
        spell1, spell2 = OB.boss_spell_ids(sb["abils"])
        a(f"    set gBossSpell[{arm * 2}] = '{spell1}'")
        a(f"    set gBossSpell[{arm * 2 + 1}] = '{spell2}'")
        boss_base, boss_dice, boss_sides = OB.BOSS_DMG[1]
        a(f"    set gBossAvgDmg[{arm}] = {jr(int(boss_base * g['boss'][3]) + boss_dice * (boss_sides + 1) / 2)}")
        boss_base, boss_dice, boss_sides = OB.BOSS_DMG[0]
        a(f"    set gWardenAvgDmg[{arm}] = {jr(int(boss_base * g['boss'][3]) + boss_dice * (boss_sides + 1) / 2)}")
    # stage rosters: gStageUnit[arm*6 + stage*2 + 0 front / 1 back]; arm 4 = the Dark Gate
    for d, f in enumerate(OB.FACTIONS + OB.GATE_LEVELS):      # standardized copies (q<arm><stage><m|r>)
        for st in range(len(f["stages"])):
            a(f"    set gStageUnit[{d * 6 + st * 2}] = '{OB.wave_unit_id(d, st, False)}'")
            a(f"    set gStageUnit[{d * 6 + st * 2 + 1}] = '{OB.wave_unit_id(d, st, True)}'")
    a(f"    set gFrontBase = {OB.WAVE_FRONT_BASE}")
    a(f"    set gFrontPer = {OB.WAVE_FRONT_PER}")
    a(f"    set gBackPer = {OB.WAVE_BACK_PER}")
    a(f"    set gFrontMax = {OB.WAVE_FRONT_MAX}")
    a(f"    set gBackMax = {OB.WAVE_BACK_MAX}")
    for d in range(4 + len(OB.GATE_LEVELS)):
        a(f"    set gWaveChamp[{d}] = '{OB.wave_champion_id(d)}'")
    a(f"    set gChampEvery = {OB.WAVE_CHAMP_EVERY}")
    a(f"    set gChampMax = {OB.WAVE_CHAMP_MAX}")
    a(f"    set gFormRow = {LY.FORM_ROW}")
    a(f"    set gFormStep = {jr(LY.FORM_STEP)}")
    a(f"    set gFormGap = {jr(LY.FORM_GAP)}")
    a(f"    set gFormChampRow = {LY.FORM_CHAMP_ROW}")
    a(f"    set gFormChampStep = {jr(LY.FORM_CHAMP_STEP)}")
    a(f"    set gBossHpGrowth = {OB.BOSS_HP_GROWTH}")
    a(f"    set gBossHpMax = {OB.BOSS_HP_FACTOR_MAX}")
    a(f"    set gBossDmgMax = {OB.BOSS_DMG_FACTOR_MAX}")
    a(f"    set gBossDmgGrowth = {OB.BOSS_DMG_GROWTH}")
    a(f"    set gBossSpellLevels = {OB.BOSS_SPELL_LEVELS}")
    for i, buff in enumerate(("BPSE", "BSTN", "BHtb", "BHbd")):      # what stuns in the 12 champions' kits and the final boss's own
        a(f"    set gStunBuff[{i}] = '{buff}'")
    a("    set gStunN = 4")
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
        spell1, spell2 = OB.boss_spell_ids(b["abils"])
        a(f"    set gBossSpell[{d * 2}] = '{spell1}'")
        a(f"    set gBossSpell[{d * 2 + 1}] = '{spell2}'")
        a(f"    set gBossAvgDmg[{d}] = {jr(OB._avg(OB.BOSS_DMG[1]))}")
        a(f"    set gWardenAvgDmg[{d}] = {jr(OB._avg(OB.BOSS_DMG[0]))}")
    tav_of = {h: k for k, (_, _, hs) in enumerate(OB.TAVERNS) for h in hs}
    for i, h in enumerate(OB.ALL_HEROES):
        a(f"    set gHeroPool[{i}] = '{h}'")
        a(f"    set gHeroTavern[{i}] = {tav_of[h]}")
    a(f"    set gHeroPoolCount = {len(OB.ALL_HEROES)}")
    a(f"    set gCastleType = '{OB.CASTLE_ID}'")
    a(f"    set gSoulType = '{OB.SOUL_ID}'")
    a(f"    set gBuyerType = '{OB.BUYER_ID}'")
    a(f"    set gCircleType = '{OB.CIRCLE_ID}'")
    for si in range(OB.KINDS):
        a(f"    set gKindName[{si}] = {jstr(OB.kind_name(si))}")
        a(f"    set gKindValue[{si}] = {OB.kind_value(si)}")
        a(f"    set gKindEffect[{si}] = {jstr(OB.kind_effect(si))}")
        a(f"    set gKindType[{si}] = {OB.KIND_TYPE[OB.KINDS_DEF[si]['type']]}")
        for k in range(OB.kind_tiers(si)):
            a(f"    set gStatItem[{si * OB.KIND_STRIDE + k}] = '{OB.stat_item_id(si, k)}'")
            if OB.KINDS_DEF[si]["type"] in ("abil", "castleabil"):
                a(f"    set gBonusAbil[{si * OB.KIND_STRIDE + k}] = '{OB.bonus_abil_id(si, k)}'")
    a(f"    set gKinds = {OB.KINDS}")

    a(f"    set gStatTiers = {OB.STAT_TIERS}")
    a(f"    set gKindStride = {OB.KIND_STRIDE}")
    a(f"    set gStatPerLevel = {OB.STAT_PER_LEVEL}")
    a(f"    set gHallX = {jr(LY.HALL_CENTRE[0])}")
    a(f"    set gHallY = {jr(LY.HALL_CENTRE[1])}")
    a(f"    set gHallSoulDY = {jr(LY.HALL_SOUL_DY)}")
    a(f"    set gCastleShopRange = {jr(OB.CASTLE_SHOP_RANGE)}")
    a(f"    set gBuyerX = {jr(LY.BUYER_POS[0])}")
    a(f"    set gBuyerY = {jr(LY.BUYER_POS[1])}")
    a(f"    set gSelectTime = {jr(SELECT_TIME)}")
    a(f"    set gFirstWaveDelay = {jr(FIRST_WAVE_DELAY)}")
    a(f"    set gWaveInterval = {jr(WAVE_INTERVAL)}")
    a(f"    set gWaveBreak = {jr(WAVE_BREAK)}")
    a(f"    set gBreakEvery = {BREAK_EVERY}")
    a(f"    set gWaveHpGrowth = {OB.WAVE_HP_GROWTH}")
    a(f"    set gWaveDmgGrowth = {OB.WAVE_DMG_GROWTH}")
    a(f"    set gGateHpPer = {OB.GATE_HP_PER_LEVEL}")
    a(f"    set gGateDmgPer = {OB.GATE_DMG_PER_LEVEL}")
    a(f"    set gTeamHpPer = {OB.TEAM_HP_PER_PLAYER}")
    a(f"    set gIncomeWaveSeconds = {OB.INCOME_WAVE_SECONDS}")
    role_hp = [OB.WAVE_MELEE_HP, OB.WAVE_RANGED_HP, OB.WAVE_CHAMP_HP]
    role_dmg = [OB.WAVE_MELEE_DMG, OB.WAVE_RANGED_DMG, OB.WAVE_CHAMP_DMG[0] + OB.WAVE_CHAMP_DMG[1]]
    for r in range(3):
        a(f"    set gRoleHp[{r}] = {float(role_hp[r])}")
        a(f"    set gRoleDmg[{r}] = {float(role_dmg[r])}")
        a(f"    set gStageHp[{r}] = {OB.WAVE_STAGE_HP[r]}")
        a(f"    set gStageDmg[{r}] = {OB.WAVE_STAGE_DMG[r]}")
    for i, bit in enumerate(OB.scale_bit_ids()):
        a(f"    set gScaleBit[{i}] = '{bit}'")
    a(f"    set gScaleHpBits = {OB.SCALE_HP_BITS}")
    a(f"    set gScaleDmgBits = {OB.SCALE_DMG_BITS}")
    a(f"    set gScaleHpStep = {OB.SCALE_HP_STEP}")
    a(f"    set gScaleDmgStep = {OB.SCALE_DMG_STEP}")
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
        elif kind == "apothecary":
            a(f"    set gApoShop = CreateUnit(p, '{uid}', {jr(x)}, {jr(y)}, 270.0)")
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
def card_point(x, y):
    """Screen point of a command card button at 800 x 600 in the hidden window."""
    return 634 + 44 * x, 491 + 43 * y


def inventory_point(slot):
    return 529 + 44 * (slot % 2), 505 + 40 * (slot // 2)


def tour_rows():
    """What the tooltip tour looks at: (name, kind, hero, level, ranks, button point, order, item). Kind 0 the champion's card, 1 the tavern, 2 the armory, 3 his learn card."""
    idx = {h: OB.ALL_HEROES.index(h) for h in OB.ALL_HEROES}
    q, w, e, r, t, d, f = card_point(0, 2), card_point(1, 2), card_point(2, 2), card_point(3, 2), card_point(2, 1), card_point(1, 1), card_point(3, 1)
    lq, lw, le, lr, lt = card_point(0, 0), card_point(1, 0), card_point(2, 0), card_point(3, 0), card_point(0, 1)

    def card(name, hero, level, ranks, point, order="", item=0):
        rows.append((name, 0, idx[hero], level, ranks, point, order, item))

    def learn(name, hero, level, ranks, point):
        rows.append((name, 3, idx[hero], level, ranks, point, "", 0))
    rows = []
    # the Dryad: unlearned, low, mid, max of her spears; passive, aura, innate, level 20
    learn("dryad-arrows-learn-unlearned", "H007", 1, [0, 0, 0, 0, 0], lw)
    card("dryad-arrows-r1", "H007", 19, [0, 1, 0, 0, 0], w)
    card("dryad-arrows-r2", "H007", 19, [0, 2, 0, 0, 0], w)
    card("dryad-arrows-r4-max", "H007", 19, [0, 4, 0, 0, 0], w)
    learn("dryad-arrows-learn-r2-offers-r3", "H007", 7, [0, 2, 0, 0, 0], lw)
    card("dryad-crit-r2", "H007", 19, [0, 0, 2, 0, 0], e)
    card("dryad-trueshot-r3", "H007", 19, [0, 0, 0, 3, 0], r)
    card("dryad-endurance-r4", "H007", 19, [0, 0, 0, 0, 4], t)
    card("dryad-poison-innate", "H007", 1, [0, 0, 0, 0, 0], d)
    card("dryad-immunity-level20", "H007", 20, [4, 4, 4, 4, 4], f)
    # the Mountain King: an active at low, mid and max, locked in the learn card, a passive, the toggle both ways
    card("mk-bolt-r1", "Hmkg", 19, [1, 0, 0, 0, 0], q)
    card("mk-bolt-r2", "Hmkg", 19, [2, 0, 0, 0, 0], q)
    card("mk-bolt-r4-max", "Hmkg", 19, [4, 0, 0, 0, 0], q)
    learn("mk-avatar-learn-locked", "Hmkg", 3, [0, 0, 0, 0, 0], lr)
    card("mk-clap-r3-long", "Hmkg", 19, [0, 3, 0, 0, 0], w)
    card("mk-bash-r2-passive", "Hmkg", 19, [0, 0, 2, 0, 0], e)
    card("mk-avatar-r1", "Hmkg", 19, [0, 0, 0, 1, 0], r)
    card("mk-spirit-innate", "Hmkg", 1, [0, 0, 0, 0, 0], d)
    card("mk-shield-level20-off", "Hmkg", 20, [4, 4, 4, 2, 4], f)
    card("mk-shield-level20-on", "Hmkg", 20, [4, 4, 4, 2, 4], f, "immolation")
    # toggles and autocast
    card("dh-immolation-r2-off", "Edem", 19, [2, 0, 0, 0, 0], q)
    card("dh-immolation-r2-on", "Edem", 19, [2, 0, 0, 0, 0], q, "immolation")
    card("dh-negative-r1", "Edem", 19, [0, 1, 0, 0, 0], w)
    card("dh-meta-r2", "Edem", 19, [0, 0, 0, 2, 0], r)
    card("lich-frostarmor-r2-autocast-off", "Ulic", 19, [0, 0, 0, 0, 2], t)
    card("lich-frostarmor-r2-autocast-on", "Ulic", 19, [0, 0, 0, 0, 2], t, "frostarmoron")
    card("lich-frostarrows-r3", "Ulic", 19, [0, 0, 3, 0, 0], e)
    card("lich-nova-r2", "Ulic", 19, [2, 0, 0, 0, 0], q)
    card("crypt-beetles-r4-summon", "Ucrl", 19, [0, 0, 4, 0, 0], e)
    card("crypt-locusts-r2-long", "Ucrl", 19, [0, 0, 0, 2, 0], r)
    card("crypt-impale-r2", "Ucrl", 19, [2, 0, 0, 0, 0], q)
    # the longest, summons, channels
    card("pit-rain-r4-longest", "Nplh", 19, [4, 0, 0, 0, 0], q)
    card("pit-doom-r2", "Nplh", 19, [0, 0, 0, 2, 0], r)
    card("pit-unholy-r1-aura", "Nplh", 19, [0, 0, 0, 0, 1], t)
    card("mage-blizzard-r3", "Hamg", 19, [3, 0, 0, 0, 0], q)
    card("mage-elemental-r4-summon", "Hamg", 19, [0, 4, 0, 0, 0], w)
    learn("mage-blizzard-learn-r1-offers-r2", "Hamg", 5, [1, 0, 0, 0, 0], lq)
    card("beast-bear-r3-summon", "Nbst", 19, [3, 0, 0, 0, 0], q)
    card("beast-stampede-r2", "Nbst", 19, [0, 0, 0, 2, 0], r)
    card("blade-drums-r3-aura", "Obla", 19, [0, 0, 0, 0, 3], t)
    card("blade-mirror-r2", "Obla", 19, [0, 0, 2, 0, 0], e)
    card("pala-wave-r2", "Hpal", 19, [2, 0, 0, 0, 0], q)
    card("tauren-shock-r2", "Otch", 19, [2, 0, 0, 0, 0], q)
    card("tauren-roar-innate", "Otch", 1, [0, 0, 0, 0, 0], d)
    card("moon-chain-r3", "Emoo", 19, [3, 0, 0, 0, 0], q)
    # the fullest card at hero level 20 before everything is maxed: seven skills on it, points left, so the Learn button too. Which button stands where, all twelve places
    for label, hero in (("lich", "Ulic"), ("mk", "Hmkg"), ("dh", "Edem")):
        for y in range(3):
            for x in range(4):
                card(f"full20-{label}-{x}{y}", hero, 20, [1, 1, 1, 1, 1], card_point(x, y), "keep")
    # the shops and the items
    rows.append(("tavern-dryad", 1, 0, 1, [0, 0, 0, 0, 0], card_point(0, 0), "", 0))
    rows.append(("tavern-mk", 1, 0, 1, [0, 0, 0, 0, 0], card_point(1, 0), "", 0))
    rows.append(("armory-fang", 2, 0, 1, [0, 0, 0, 0, 0], card_point(0, 0), "", 0))
    rows.append(("armory-hammer", 2, 0, 1, [0, 0, 0, 0, 0], card_point(3, 0), "", 0))
    rows.append(("circle-agility", 4, 0, 1, [0, 0, 0, 0, 0], card_point(1, 1), "", 0))
    card("item-fang-r2", "Hmkg", 5, [0, 0, 0, 0, 0], inventory_point(0), "", OB.premium_item_id(0, 2))
    card("item-fang-r5-max", "Hmkg", 5, [0, 0, 0, 0, 0], inventory_point(0), "", OB.premium_item_id(0, 5))
    card("item-axe-r3", "Hmkg", 5, [0, 0, 0, 0, 0], inventory_point(0), "", OB.premium_item_id(2, 3))
    if os.environ.get("CD_TOUR") == "ui2":
        again = ("dh-immolation-r2-off", "dh-immolation-r2-on", "mk-shield-level20-off", "mk-shield-level20-on", "dryad-immunity-level20", "mk-bolt-r1", "mk-bolt-r2", "mk-bolt-r4-max",
                 "lich-nova-r2", "mage-blizzard-r3", "pit-rain-r4-longest", "pit-doom-r2", "dh-negative-r1", "dh-meta-r2", "tauren-shock-r2", "pala-wave-r2", "moon-chain-r3", "beast-bear-r3-summon",
                 "mk-clap-r3-long", "crypt-impale-r2", "blade-mirror-r2", "dryad-endurance-r4")
        rows = [r for r in rows if r[0] in again or r[0].startswith("full20-")]
    return rows


def build_tour_table(a):
    rows = tour_rows()
    for n, (name, kind, hero, level, ranks, (x, y), order, item) in enumerate(rows):
        a(f"    set gTourName[{n}] = {jstr(name)}")
        a(f"    set gTourKind[{n}] = {kind}")
        a(f"    set gTourHero[{n}] = {hero}")
        a(f"    set gTourLevel[{n}] = {level}")
        a(f"    set gTourX[{n}] = {x}")
        a(f"    set gTourY[{n}] = {y}")
        a(f"    set gTourOrder[{n}] = {jstr(order)}")
        a(f"    set gTourItem[{n}] = {chr(39) + item + chr(39) if item else 0}")
        for s, rank in enumerate(ranks):
            a(f"    set gTourRank[{n * 5 + s}] = {rank}")
    a(f"    set gTourN = {len(rows)}")
    a(f"    set gTestOnly = {jstr('tour')}")


def native_areas(game):
    """The game's own Area of Effect of every ability, by level: code -> {level: area}."""
    cells = slk_cells(game.read("Units\\AbilityData.slk"))
    col = {cell[0].strip(b'"').decode(): c for (r, c), cell in cells.items() if r == 1}
    out = {}
    for (r, c), cell in cells.items():
        if c != col["alias"] or r == 1:
            continue
        areas = out.setdefault(cell[0].strip(b'"').decode(), {})
        for level in range(1, 5):
            value = cells.get((r, col[f"Area{level}"]), (None,))[0]
            try:
                areas[level] = float(value)
            except (TypeError, ValueError):
                pass
    return out


def spell_area(area_of, aid, level):
    """A spell's real radius at a level: the reference's own value, or the native row it is built on."""
    base, _custom, mods = XHS.ABILS[aid]
    for field, _kind, lvl, _data, value in mods:
        if field == "aare" and lvl == level:
            return float(value)
    native = area_of.get(base, {})
    return native.get(level, native.get(max(native, default=0), 0.0))


def build_cast_table(a):
    """The self-test's table of every champion's castable abilities (test build only): gen/xhs_text.py + the summons of the data."""
    targets = {"none": 0, "enemy": 1, "point": 2, "ally": 3, "self": 4, "corpse": 5}
    effects = {"damage": 1, "heal": 2, "summon": 3, "buff": 4, "morph": 5, "split": 6, "toggle": 7, "foebuff": 8, "allybuff": 9, "images": 10}
    area_of = native_areas(GameData(GAME_DIR))
    n = 0
    for c, h in enumerate(OB.ALL_HEROES):
        uabi = next((v for (f, _k, _l, _p, v) in XHS.UNITS[h][2] if f == "uabi"), "")
        extras = [x for x in uabi.split(",") if x and x != "AInv"] + XHS.LEVEL20[h][0]
        # the innate and level 20 abilities first: the Tauren's roar must be on before his Stomp and Shockwave strike twice
        rows = [aid for aid in extras + OB.HERO_SKILLS[h] if OB.XHS_SKILLS[aid][2] and aid != "ACro"]
        # a split or a demon form stays on, so it comes last
        rows.sort(key=lambda aid: OB.XHS_SKILLS[aid][4].split(":")[0] in ("split", "morph"))
        for aid in rows:
            name, _kind, order, target, effect = OB.XHS_SKILLS[aid]
            what, detail, count = (effect.split(":") + ["", ""])[:3]
            if what == "images":
                detail, count = "", detail
            a(f"    set gCastHero[{n}] = {c}")
            a(f"    set gCastAbil[{n}] = '{aid}'")
            a(f"    set gCastName[{n}] = {jstr(name)}")
            a(f"    set gCastOrder[{n}] = {jstr(order)}")
            a(f"    set gCastTarget[{n}] = {targets[target]}")
            a(f"    set gCastEffect[{n}] = {effects[what]}")
            a(f"    set gCastUnit[{n}] = {chr(39) + detail + chr(39) if detail else 0}")
            a(f"    set gCastCount[{n}] = {count or 0}")
            for level in range(1, 6):
                area = spell_area(area_of, aid, level)
                if area:
                    a(f"    set gCastArea[{n * 6 + level}] = {jr(area)}")
            n += 1
    a(f"    set gCastN = {n}")


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


def slk_cells(raw):
    """A SYLK table: (row, column) -> (raw value, byte offset of the record, the record). Records keep their row until the next Y."""
    cells = {}
    x = y = None
    offset = 0
    for line in raw.split(b"\n"):
        record = line.rstrip(b"\r")
        if record.startswith(b"C;"):
            value = None
            for part in record.split(b";")[1:]:
                if part[:1] == b"X":
                    x = int(part[1:])
                elif part[:1] == b"Y":
                    y = int(part[1:])
                elif part[:1] == b"K":
                    value = part[1:]
            cells[(y, x)] = (value, offset, record)
        offset += len(line) + 1
    return cells


def ability_slk_doom_fix(game):
    """The game's own Units\\AbilityData.slk, whole, with one cell changed: Doom's Max Creep Level at level 2 (docs/wc3-127-gotchas.md).

    The native row has one level and "-" there. A map's Doom with two levels then refuses every monster of the creep race at level 2, and no
    object field reaches that cell. The map carries the game's table with this one difference; generated at build, never committed.
    """
    raw = game.read("Units\\AbilityData.slk")
    if raw is None:
        raise SystemExit("no Units\\AbilityData.slk in the game")
    cells = slk_cells(raw)
    col = {cell[0]: c for (r, c), cell in cells.items() if r == 1}
    rows = [r for (r, c), cell in cells.items() if c == col[b'"alias"'] and cell[0] == b'"ANdo"']
    if len(rows) != 1:
        raise SystemExit(f"Doom rows in the ability table: {rows}")
    row = rows[0]
    first, second = cells[(row, col[b'"DataD1"'])], cells[(row, col[b'"DataD2"'])]
    if first[0] != b"5" or second[0] != b'"-"':
        raise SystemExit(f"Doom's creep level cells are not what this fix is for: {first[0]} {second[0]}")
    new_record = second[2].replace(b'K"-"', b"K" + first[0])
    fixed = raw[:second[1]] + new_record + raw[second[1] + len(second[2]):]
    after = slk_cells(fixed)
    changed = sorted(k for k in set(cells) | set(after) if cells.get(k, (None,))[0] != after.get(k, (None,))[0])
    if changed != [(row, col[b'"DataD2"'])] or raw.count(b"\r\n") != fixed.count(b"\r\n"):
        raise SystemExit(f"the ability table differs in more than the one cell: {changed}")
    return fixed


def misc_constants(game):
    """war3mapMisc.txt = the game's full [Misc] gameplay constants (Units\\MiscGame.txt) with our edits.
    The whole section is written, like the World Editor does, so nothing falls back to 0."""
    lines = game.read("Units\\MiscGame.txt").decode("latin1").splitlines()
    edits = {"MaxHeroLevel": str(OB.MAX_HERO_LEVEL), "MaxUnitSpeed": str(OB.BOSS_SPEED)}
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        out.append(f"{key}={edits[key]}" if key in edits else line)
    return ("\r\n".join(out) + "\r\n").encode("latin1")


REQUIRED_SCRIPT_DATA = ["set gBuyerType = ", "set gBuyerX = ", "set gScaleBit[0] = ", "set gWaveHpGrowth = ", "set gTeamHpPer = ", "set gIncomeWaveSeconds = ", "set gFinalType = ", "set gFinalBit[0] = ", "set gFinalSpell[0] = ", "set gFinalHpBase = ", "set gBankItem = ", "set gIncomeStep = ", "set gPremItem[1] = ", "set gPremCount = ",
                        "set gShopFxCount = ", "set gDevCount = ", "set gAttrPerLevel = ", "set gReachItem = ",
                        "set gGateState[11] = ", "set gStageUnit[0] = ", "set gEpicItem[5] = ", "set gStatItem[0] = ", "set gHeroPool[0] = ",
                        "set gPotCount = ", "set gHeroSkill[0] = ", "set gGrantN = ", "set gDrumAura[4] = ",
                        ]


def check_tooltips():
    """An ability text that is too long crashes the game while the map loads: stop the build, naming it."""
    texts = [(f"{aid} {where}", field, value) for (aid, where, field, value) in OB.tooltip_texts()]
    texts += [(f"{uid} {field}", field, value) for (_base, uid, mods) in OB.custom_items() for (field, _k, value) in mods if field in ("utub", "ides")]
    long_lines = OB.TIPS.check(texts)
    print(f"tooltips: {len(texts)} texts, longest {max(len(v.encode('utf-8')) for (_o, _f, v) in texts)} bytes, {len(long_lines)} rows wrap")
    for owner, line in long_lines:
        print(f"  wraps: {owner}: {line}")


def check_script_data(script):
    """Fail the build if a data block vanished from InitData. An edit once deleted the Bank / premium / dev-name
    data: the map still compiled and ran, but Bank buys and item upgrades silently did nothing (2026-10-31)."""
    missing = [s for s in REQUIRED_SCRIPT_DATA if s not in script]
    if missing:
        sys.exit("InitData is missing: " + ", ".join(missing))


def check_icons(game, files):
    """Every icon path in our object data (unit/item icons, custom ability icons) must exist in the game MPQs or the map. A missing one shows as
    a plain GREEN square in game (Shadow Crown pointed at a non-existent BTNCrownOfKings, 2026-11-01)."""
    paths = set()
    for tables in ((OB.custom_units(), OB.original_unit_mods()), (OB.custom_items(), OB.original_item_mods())):
        for objs in tables:
            for obj in objs:
                for m in obj[-1]:
                    if m[0] in ("iico", "uico") and m[-1]:
                        paths.add(m[-1])
    for obj in OB.custom_abilities():
        for m in obj[-1]:
            if m[0] in ("aart", "arar") and m[-1]:
                paths.add(m[-1])
    missing = []
    for p in sorted(paths):
        if p in files:
            continue
        if not game.read(p):            # GameData.read returns None for a missing file
            missing.append(p)
    if missing:
        sys.exit("Icons not found in the game or the map: " + ", ".join(missing))


def check_fx(game, files):
    """Every special-effect model the script plays (objects.FX) must exist - a wrong path plays nothing at all."""
    missing = [p for p in sorted(set(OB.FX.values()))
               if p and p not in files and not game.read(p[:-4] + ".mdx")]     # .mdl in data = .mdx in the MPQs
    if missing:
        sys.exit("Effect models not found in the game: " + ", ".join(missing))


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


PROBE_GLOBALS = """    // balance probe: only in --probe maps
    integer gPrHero = 0
    integer gPrCasts = 0
    integer gPrCastOrder = 0
    integer gPrDuelPhase = 0
    integer gPrFangTries = 0
    integer gPrDuelLevel = 1
    integer gPrDuelBudget = 1000
    boolean gPrDuelNexus = false
    real gPrDuelContact = -1.0
    real gPrDuelStart = 0.0
    integer gPrBossCasts = 0
    real gPrBossChannelAt = 0.0
    boolean gPrBossFinished = false
    boolean gPrChannel = false
    real gPrChannelAt = 0.0
    integer gPrOtherN = 0
    integer array gPrOtherType
    real array gPrOtherDmg
    integer gPrCastRow = 0
    real gPrCastAt = -100.0
    unit gPrBestU = null
    real gPrBossAt = -1.0
    real gPrBossLogAt = 0.0
    real gPrBossMax = 0.0
    unit gPrBoss = null
    integer gPrDeathsAtBoss = 0
    boolean gPrBossLogged = false
    integer gPrMode = 0
    integer gPrSeed = 1
    integer gPrMaxWave = 0
    integer gPrStallWave = 3
    integer gPrStallAlive = 4
    boolean gPrStalling = false
    real gPrDuration = 300.0
    real gPrEngage = 1000.0
    real gPrSafeDist = 1050.0
    real gPrTowerRange = 750.0
    real gPrPushHits = 0.0
    integer gPrAlive = 0
    real gPrBaseArmor = 0.0
    real gPrArmorStep = 2.0
    real gPrTowerHit = 25000.0
    real gPrNexusHit = 27500.0
    real gPrBossHit = 2400.0
    real gPrFromWave = 0.0
    real gPrFromTower = 0.0
    real gPrFromNexus = 0.0
    real gPrFromBoss = 0.0
    real gPrFromOther = 0.0
    boolean gPrBuyDone = false
    real gPrPriceBase = 100.0
    real gPrPriceXp = 250.0
    real gPrPriceGrowth = 1.05
    integer gPrPotionPrice = 100
    string gPrBuy = ""
    string gPrCycle = ""
    integer gPrBuyAt = 0
    integer gPrCycleAt = 0
    integer gPrSkillNext = 0
    integer gPrSpent = 0
    integer gPrHits = 0
    integer gPrTowerHits = 0
    integer gPrNexusHits = 0
    integer gPrWave = 0
    integer gPrWaveCount = 0
    boolean gPrWaveOpen = false
    boolean gPrDone = false
    boolean gPrTowerDown = false
    boolean gPrNexusDown = false
    boolean gPrBossDown = false
    real gPrWaveAt = 0.0
    real gPrFirstHit = -1.0
    real gPrFirstDeal = -1.0
    real gPrTaken = 0.0
    real gPrTakenAll = 0.0
    real gPrHeroWaveRaw = 0.0
    real gPrHeroWaveHp = 0.0
    real gPrHeroOtherRaw = 0.0
    real gPrHeroOtherHp = 0.0
    real gPrOtherRaw = 0.0
    real gPrOtherHp = 0.0
    real gPrHpMin = 0.0
    real gPrBest = 0.0
    real gPrBestX = 0.0
    real gPrBestY = 0.0
    integer gPrDeathsWave = 0
    integer gPrTavernTries = 0
    integer gPrPendType = 0
    integer gPrPendKind = 0
    integer gPrPendStep = 0
    integer gPrPendPrice = 0
    integer gPrPendGold = 0
    real gPrPendAt = 0.0
    string gPrPendName = ""
    real gPrEX = 0.0
    real gPrEY = 0.0
    real gPrFarX = 0.0
    real gPrFarY = 0.0
    real gPrPotionAt = -100.0
    real gPrOrderAt = -100.0
    real gPrSpendAt = 0.0
    real gPrBeatAt = 0.0
    timer gPrClock = null
    trigger gPrDealTrig = null
"""


def apply_probe(script):
    """The production script, plus gen/probe.j and two hooks. No production line changes."""
    cfg = {"hero": 0, "mode": 0, "seed": 1, "buy": "", "cycle": "", "duration": 300, "max_wave": 0, "stall_wave": 3, "duel_level": 1, "duel_budget": 1000, "duel_nexus": False}
    cfg.update(PROBE)
    def once(text, old, new):
        assert text.count(old) == 1, old
        return text.replace(old, new)
    assert not TEST
    def avg(dmg):
        base, dice, sides = dmg
        return base + dice * (sides + 1) / 2.0
    hero_id = OB.ALL_HEROES[int(cfg["hero"])]
    base_armor = OB.hero_base_armor(hero_id)
    conf = "\n".join([
        f"    set gPrHero = {int(cfg['hero'])}", f"    set gPrMode = {int(cfg['mode'])}", f"    set gPrSeed = {int(cfg['seed'])}",
        f"    set gPrMaxWave = {int(cfg['max_wave'])}", f"    set gPrStallWave = {int(cfg['stall_wave'])}", f"    set gPrDuration = {float(cfg['duration'])}",
        f'    set gPrBuy = "{cfg["buy"]}"', f'    set gPrCycle = "{cfg["cycle"]}"',
        f"    set gPrDuelLevel = {int(cfg['duel_level'])}", f"    set gPrDuelBudget = {int(cfg['duel_budget'])}", f"    set gPrDuelNexus = {'true' if cfg['duel_nexus'] else 'false'}",
        f"    set gPrPriceBase = {float(OB.STAT_BASE_PRICE)}", f"    set gPrPriceGrowth = {float(OB.STAT_PRICE_GROWTH)}",
        f"    set gPrTowerHit = {avg(OB.TURRET_DMG)}", f"    set gPrNexusHit = {avg(OB.NEXUS_DMG)}", f"    set gPrBossHit = {avg(OB.BOSS_DMG[1])}",
        f"    set gPrBaseArmor = {float(base_armor)}", f"    set gPrArmorStep = {float(OB.KINDS_DEF[3]['value'])}", f"    set gPrPushHits = {float(cfg.get('push_hits', 0))}",
    ])
    with open(os.path.join(ROOT, "gen", "probe.j"), encoding="utf-8") as fh:
        probe = fh.read()
    script = script.replace("\r\n", "\n")
    script = once(script, "endglobals\n", PROBE_GLOBALS + "endglobals\n")
    script = once(script, "function InitGame takes nothing returns nothing\n", probe + "\nfunction InitGame takes nothing returns nothing\n")
    script = once(script, "    call InitData()\n    set gKingdom = Player(14)\n", "    call InitData()\n" + conf + "\n    call ProbeEarly()\n    set gKingdom = Player(14)\n")
    script = once(script, "    call TimerStart(CreateTimer(), 0.5, false, function SetupChampionSelect)\n", "    call TimerStart(CreateTimer(), 0.5, false, function SetupChampionSelect)\n    call TimerStart(CreateTimer(), 2.0, false, function ProbeBoot)\n")
    return script.replace("\n", "\r\n")


def main():
    install = "--no-install" not in sys.argv and not TEST and PROBE is None
    rng = random.Random(SEED)
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)

    points = build_terrain(rng)
    w3e = WF.write_w3e("K", GROUND, CLIFFS, NPTS, NPTS, float(ORIGIN), float(ORIGIN), points)
    walk = cell_walk()
    walls, deco = build_walls(walk, rng)
    pw, path = build_pathing(walk)
    print(f"{len(walls)} wall pieces, {len(deco)} torches/braziers")
    script = build_script()
    if PROBE is not None:
        script = apply_probe(script)
    script_path = os.path.join(ROOT, "dist", "war3map.j")
    with open(script_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(script)
    pjass(script_path)
    check_script_data(script)
    check_object_bases()
    OB.check_scaling()
    check_tooltips()

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
        "war3map.w3a": WF.write_w3a(OB.original_ability_mods(), OB.custom_abilities()),
        "war3map.w3h": WF.write_w3u(*OB.custom_buffs()),
        "war3map.w3q": WF.write_w3a([], OB.custom_upgrades()),
        "war3mapPreview.tga": SP.preview_tga(art),
    }
    for path, tile in SP.loading_tiles(art).items():          # TechTools loading screen
        files[path] = WF.write_blp_paletted(tile, dither=True, mips=False)
    game = GameData(GAME_DIR)
    files.update(IC.stat_icons(game))                          # Str / Agi / Int shop icons
    files["war3mapMisc.txt"] = misc_constants(game)            # gameplay constants: hero max level
    files["Units\\AbilityData.slk"] = ability_slk_doom_fix(game)
    check_icons(game, files)
    check_fx(game, files)
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
