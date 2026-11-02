#!/usr/bin/env python3
"""The map's geometry on paper, before the engine: every lane, stage and cap-sized army, with a picture.

    tools/layout_audit.py [preview.png]      exit 1 on any failure; the picture defaults to dist/layout-preview.png

It checks the coordinates the build uses. What the engine then does with them is the self-test's job (TestFormTick).
"""
import math
import os
import sys
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gen"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import layout as LY          # noqa: E402
import objects as OB         # noqa: E402

STEP, GAP, ROW = LY.FORM_STEP, LY.FORM_GAP, LY.FORM_ROW
CHAMP_STEP, CHAMP_ROW = LY.FORM_CHAMP_STEP, LY.FORM_CHAMP_ROW
MARGIN = 64.0
fails = []


def check(ok, text):
    print(("PASS " if ok else "FAIL ") + text)
    if not ok:
        fails.append(text)


def lanes():
    """(lane, waypoints, tower, Nexus, tower spawn, Nexus spawn, gate pieces)"""
    for L in range(8):
        yield L, LY.lane_waypoints(L), LY.tower_pos(L), LY.nexus_pos(L), LY.tower_spawn(L), LY.nexus_spawn(L), LY.lane_gate(L)
    for L, (wps, tower, nexus, tspawn, nspawn, gate) in LY.GATE_GEOMETRY.items():
        yield L, wps, tower, nexus, tspawn, nspawn, gate


def walk(x, y):
    return LY.walkable(LY.classify(x, y)[0])


def army_depth():
    """The deepest wave: ranged, then melee, then champions, as SpawnWave lays them out."""
    ranks = lambda count, per: (count - 1) // per + 1 if count else 0
    # from the rear rank's centres to the centres of the first rank, plus the biggest unit's radius (64) in front
    depth = STEP * ranks(OB.WAVE_BACK_MAX, ROW) + GAP + STEP * ranks(OB.WAVE_FRONT_MAX, ROW) + GAP + CHAMP_STEP * (ranks(OB.WAVE_CHAMP_MAX, CHAMP_ROW) - 1) + 64.0
    half = max((ROW - 1) * STEP / 2.0 + 48.0, (min(OB.WAVE_CHAMP_MAX, CHAMP_ROW) - 1) * CHAMP_STEP / 2.0 + 64.0)
    return depth, half


def flood(blocked):
    """Connected floor, on the 128 grid, walking across nothing in `blocked` (cells of closed gates)."""
    width = LY.MAP_TILES
    cell = lambda i, j: (-LY.HALF + 64 + 128 * i, -LY.HALF + 64 + 128 * j)
    seen = {}
    parts = 0
    for j0 in range(width):
        for i0 in range(width):
            if (i0, j0) in seen or (i0, j0) in blocked or not walk(*cell(i0, j0)):
                continue
            parts += 1
            seen[(i0, j0)] = parts
            todo = deque([(i0, j0)])
            while todo:
                i, j = todo.popleft()
                for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= a < width and 0 <= b < width and (a, b) not in seen and (a, b) not in blocked and walk(*cell(a, b)):
                        seen[(a, b)] = parts
                        todo.append((a, b))
    return seen, cell


def gate_cells(pieces):
    out = set()
    for (kind, x, y, _f) in pieces:
        along_x = kind == "ITg1"
        for k in range(-320 + 64, 320, 128):
            px, py = (x + k, y) if along_x else (x, y + k)
            out.add((int((px + LY.HALF) // 128), int((py + LY.HALF) // 128)))
    return out


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist", "layout-preview.png")
    depth, half = army_depth()
    print(f"the biggest army: {OB.WAVE_FRONT_MAX} melee, {OB.WAVE_BACK_MAX} ranged, {OB.WAVE_CHAMP_MAX} champions: {depth:.0f} deep, {2 * half:.0f} wide at most")
    rects = []
    all_gates = set()
    travel = {}
    for L, wps, tower, nexus, tspawn, nspawn, gate in lanes():
        for piece in gate:
            all_gates |= gate_cells([piece])
        length = sum(math.dist(a, b) for a, b in zip(wps, wps[1:]))
        travel[L] = length
        for label, anchor, building in (("tower", tspawn, tower), ("Nexus", nspawn, nexus)):
            dx, dy = wps[1][0] - anchor[0], wps[1][1] - anchor[1]
            dist = math.hypot(dx, dy)
            fx, fy = dx / dist, dy / dist
            check(abs(fx) + abs(fy) == 1.0, f"lane {L} {label}: forward is along an axis ({fx:g}, {fy:g})")
            check(dist >= depth + 350.0, f"lane {L} {label}: the first waypoint is {dist:.0f} ahead, past the army ({depth:.0f}), so nobody turns back")
            back = (anchor[0] - building[0]) * fx + (anchor[1] - building[1]) * fy
            check(back >= 240.0, f"lane {L} {label}: the rear rank stands {back:.0f} in front of the building")
            bad = 0
            for p in range(0, int(depth) + 1, 32):
                for q in range(int(-half), int(half) + 1, 32):
                    x = anchor[0] + fx * p - fy * q
                    y = anchor[1] + fy * p + fx * q
                    if not walk(x, y):
                        bad += 1
            check(bad == 0, f"lane {L} {label}: all of the army's room is floor ({bad} points are not)")
            hit = [(px, py) for (kind, gx, gy, _f) in gate for (px, py) in [(gx, gy)]
                   if -64.0 - 48.0 <= (px - anchor[0]) * fx + (py - anchor[1]) * fy <= depth + 64.0 and abs((px - anchor[0]) * -fy + (py - anchor[1]) * fx) <= half + 320]
            check(not hit, f"lane {L} {label}: no gate or its post in the army's room")
            rects.append((L, anchor, fx, fy))
        # the road: wide floor all the way
        narrow = 0
        for a, b in zip(wps[:-2], wps[1:-1]):
            seg = math.dist(a, b)
            ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
            for s in range(0, int(seg), 64):
                x, y = a[0] + ux * s, a[1] + uy * s
                if not (walk(x - uy * 256, y + ux * 256) and walk(x + uy * 256, y - ux * 256)):
                    narrow += 1
        check(narrow == 0, f"lane {L}: the road has 512 of floor all along, it is {length:.0f} long to the castle")
    # walls: with the gates closed, every lane and gate is its own room
    seen, cell = flood(all_gates)
    plaza = seen[(LY.MAP_TILES // 2, LY.MAP_TILES // 2)]
    rooms = {}
    for L, wps, tower, nexus, tspawn, nspawn, gate in lanes():
        here = seen.get((int((tspawn[0] + LY.HALF) // 128), int((tspawn[1] + LY.HALF) // 128)))
        rooms[L] = here
        check(here is not None and here != plaza, f"lane {L}: with its gate closed, the plaza cannot reach it")
    check(len(set(rooms.values())) == 12 - 1 or len(set(rooms.values())) == 12, f"the lanes are separate rooms: {len(set(rooms.values()))} rooms for 12 lanes (Level 4 and 5 are one room only if Level 5's gate is open)")
    hall = seen.get((int((LY.HALL_CENTRE[0] + LY.HALF) // 128), int((LY.HALL_CENTRE[1] + LY.HALF) // 128)))
    check(hall is not None and hall != plaza and hall not in rooms.values(), "the Hall of Champions is a room of its own")
    grove = seen.get((int((LY.GROVE_BUILDINGS[0][1] + LY.HALF) // 128), int((LY.GROVE_BUILDINGS[0][2] + LY.HALF) // 128)))
    check(grove == plaza, "the grove opens into the plaza")
    # and with them open, everything reaches the castle
    seen2, _cell = flood(set())
    plaza2 = seen2[(LY.MAP_TILES // 2, LY.MAP_TILES // 2)]
    for L, wps, tower, nexus, tspawn, nspawn, gate in lanes():
        check(seen2.get((int((tspawn[0] + LY.HALF) // 128), int((tspawn[1] + LY.HALF) // 128))) == plaza2, f"lane {L}: with its gate open, it reaches the castle")
    # the playable area and every map edge
    edge = 0
    for j in range(LY.MAP_TILES):
        for i in range(LY.MAP_TILES):
            x, y = cell(i, j)
            if walk(x, y) and not (LY.PLAY_MINX + 128 <= x <= LY.PLAY_MAXX - 128 and LY.PLAY_MINY + 128 <= y <= LY.PLAY_MAXY - 128):
                edge += 1
    check(edge == 0, "all floor is at least a tile inside the playable area")
    bx, by = LY.BUYER_POS
    check(not walk(bx, by) and math.hypot(bx, by) <= OB.CASTLE_SHOP_RANGE - 128, f"a dead champion's buyer stands in the dark, {math.hypot(bx, by):.0f} from the castle (its shop reaches {OB.CASTLE_SHOP_RANGE:.0f})")
    print("the way to the castle: " + ", ".join(f"lane {L} {v:.0f}" for L, v in travel.items()))
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("no PIL: no picture")
        return 1 if fails else 0
    scale = 16
    size = LY.HALF * 2 // scale
    img = Image.new("RGB", (size, size), (10, 6, 18))
    px = img.load()
    colours = {"plaza": (96, 96, 110), "lane": (92, 72, 54), "base": (120, 50, 50), "hall": (60, 120, 150), "grove": (40, 110, 60), "shared": (110, 60, 130)}
    for y in range(size):
        wy = LY.HALF - y * scale
        for x in range(size):
            kind = LY.classify(-LY.HALF + x * scale, wy)[0]
            if kind in colours:
                px[x, y] = colours[kind]
    draw = ImageDraw.Draw(img)
    to_px = lambda p: ((p[0] + LY.HALF) / scale, (LY.HALF - p[1]) / scale)
    for L, wps, tower, nexus, tspawn, nspawn, gate in lanes():
        draw.line([to_px(p) for p in wps], fill=(255, 220, 90), width=1)
        for b, c in ((tower, (255, 80, 80)), (nexus, (255, 0, 255))):
            x, y = to_px(b)
            draw.rectangle([x - 8, y - 8, x + 8, y + 8], outline=c, width=2)
        for (kind, gx, gy, _f) in gate:
            x, y = to_px((gx, gy))
            d = (20, 4) if kind == "ITg1" else (4, 20)
            draw.rectangle([x - d[0], y - d[1], x + d[0], y + d[1]], fill=(120, 200, 255))
    for (L, anchor, fx, fy) in rects:
        corners = [(anchor[0] + fx * p - fy * q, anchor[1] + fy * p + fx * q) for p, q in ((0, -half), (depth, -half), (depth, half), (0, half))]
        draw.polygon([to_px(c) for c in corners], outline=(90, 255, 120))
        mid = to_px((anchor[0] + fx * depth, anchor[1] + fy * depth))
        draw.line([to_px(anchor), mid], fill=(90, 255, 120), width=2)
    img.save(target)
    print(f"picture: {target}")
    print(f"{len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
