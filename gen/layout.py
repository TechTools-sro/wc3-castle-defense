"""Map geometry for "TechTools Castle Defence" (hero lane defense).

128x128 map. The castle sits in the centre plaza. Four fronts (N, E, S, W) run
outward; each front is two walled lanes (left/right) that meet in front of the
enemy base at the far end. Every lane belongs to one player's champion:
4 fronts x 2 lanes = 8 players. Everything that is not a lane, the plaza, a base
or the Hall of Champions is abyss (unwalkable void).

Arm-local coordinates: u = across the arm, v = outward from the castle.
Arm d: 0=North, 1=East, 2=South, 3=West (clockwise rotation of the North arm).
Lane L = 2*d + side; side 0 = left (u<0), 1 = right (u>0). Lane L = Player(L).
"""

MAP_TILES = 128                        # v4.3 (Jiri): armies and summons need room. Every lane and gate twice as wide, the plaza bigger
HALF = MAP_TILES * 128 // 2            # 8192
CAMCOMP = (6, 6, 4, 8)                 # boundary tiles: left, right, bottom, top (WE default)
PLAY_MINX = -HALF + CAMCOMP[0] * 128   # -7424
PLAY_MAXX = HALF - CAMCOMP[1] * 128    # 7424
PLAY_MINY = -HALF + CAMCOMP[2] * 128   # -7680
PLAY_MAXY = HALF - CAMCOMP[3] * 128    # 7168

PLAZA = 2304                           # plaza = |x|,|y| <= PLAZA (all bounds on the 128 grid)
LANE_IN, LANE_OUT = 128, 1408          # lane corridor spans |u| in [LANE_IN, LANE_OUT]: 1280 wide (two gate pieces), a wall of 256 between a front's lanes
LANE_END = 5760                        # lanes run v in [PLAZA, LANE_END]: as long as before, only the plaza moved them out
BASE_START, BASE_END = 5760, 6656      # each lane ends in its OWN enemy base room
ROOM_IN, ROOM_OUT = 128, 1536           # base room spans |u| in [ROOM_IN, ROOM_OUT]; |u| < ROOM_IN stays a wall

# Hall of Champions (champion select): v3.8 (Jiri) a SMALL room in the empty top-right (NE) corner, far from every
# spawn point. The old 1536-wide hall in the NW lay 512 from the Frozen Gate tower spawn, and a big wave that did not
# fit there was placed by the engine onto the nearest free floor = into the hall (CreateUnit ignores walls).
HALL_CENTRE = (6272, 6144)             # inside the camera bounds, far from every lane, gate and base room
HALL_HALF = 384                        # 768 x 768 (6 x 6 tiles): the tavern + the invisible buyers, nothing else

DIR_NAMES = ["North", "East", "South", "West"]
DIR_FACING_IN = [270.0, 180.0, 90.0, 0.0]


def from_arm(d, u, v):
    if d == 0:
        return (u, v)
    if d == 1:
        return (v, -u)
    if d == 2:
        return (-u, -v)
    return (-v, u)


def to_arm(d, x, y):
    if d == 0:
        return (x, y)
    if d == 1:
        return (-y, x)
    if d == 2:
        return (-x, -y)
    return (y, -x)


def classify(x, y):
    """-> (kind, index). kind: boundary, plaza, lane, base, hall, void."""
    if not (PLAY_MINX <= x <= PLAY_MAXX and PLAY_MINY <= y <= PLAY_MAXY):
        return ("boundary", -1)
    if abs(x) <= PLAZA and abs(y) <= PLAZA:
        return ("plaza", -1)
    hx, hy = HALL_CENTRE
    if abs(x - hx) <= HALL_HALF and abs(y - hy) <= HALL_HALF:
        return ("hall", -1)
    for (x0, y0, x1, y1) in GROVE_RECTS:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return ("grove", -1)
    for idx, rects in enumerate((SHARED_RECTS, LEVEL3_RECTS, LEVEL4_RECTS, LEVEL5_RECTS)):
        for (x0, y0, x1, y1) in rects:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return ("shared", idx)        # idx 0..3 = gate Level 2..5
    for d in range(4):
        u, v = to_arm(d, x, y)
        au = abs(u)
        if PLAZA <= v < LANE_END and LANE_IN <= au <= LANE_OUT:
            return ("lane", d)
        if BASE_START <= v <= BASE_END and ROOM_IN <= au <= ROOM_OUT:
            return ("base", d)
    return ("void", -1)


def walkable(kind):
    return kind in ("plaza", "lane", "base", "hall", "grove", "shared")


# --------------------------------------------------------------------------
def lane_side(L):
    return -1 if L % 2 == 0 else 1


# A wave stands in ranks across its lane (SpawnRanks). The engine moves a unit that touches another when it is placed, and rows swap then:
# units with a collision of 48 at 96 apart got behind the rank at their back. At 128 apart they stay where they are put.
FORM_ROW, FORM_STEP, FORM_GAP = 8, 128.0, 64.0
FORM_CHAMP_ROW, FORM_CHAMP_STEP = 6, 192.0

LANE_U = 768                # the middle of the lane
LANE_WAYPOINTS_ARM = [      # (|u| * side, v); the last point is the castle. Point 1 lies far below the tower spawn: a whole army stands between them
    (LANE_U, 4128),         # 0 spawn (tower; the script switches to the Nexus once the tower falls)
    (LANE_U, 2848),         # 1
    (LANE_U, 2400),         # 2
    (LANE_U, 1800),         # 3 plaza
    (LANE_U, 1100),         # 4 plaza
    (0, 0),                 # 5 castle
]


def lane_waypoints(L):
    d, s = L // 2, lane_side(L)
    return [from_arm(d, s * u, v) for (u, v) in LANE_WAYPOINTS_ARM]


def hero_spot(L):
    """Where the lane's champion appears / revives: on his own Champion's Circle at the lane entrance."""
    return lane_marker(L)


def lane_marker(L):
    """Entrance of the lane (just past the plaza edge): coloured Circle of Power of the lane's player."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, PLAZA + 288)


def lane_gate(L):
    """Icecrown gates across the lane entrance: two pieces (destructable id, x, y, facing). A piece has a 640x128 footprint
    (Gate1Path 20x4 cells), two of them = exactly the lane width. ITg1 (facing 270) spans x, ITg3 (facing 0) spans y."""
    d, s = L // 2, lane_side(L)
    pieces = []
    for off in (-320, 320):
        x, y = from_arm(d, s * LANE_U + off, PLAZA + 64)
        pieces.append(("ITg1", x, y, 270.0) if d % 2 == 0 else ("ITg3", x, y, 0.0))
    return pieces


def lane_label(L):
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, PLAZA + 420)


def nexus_pos(L):
    """The lane's own enemy Nexus (spawns the waves of this lane, its boss rises from it)."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 6208)


def tower_pos(L):
    """The lane's own strong enemy tower, in the lane centre far in front of its Nexus: tower (range 750) and
    Nexus (range 700, measured from its big footprint) never cover the same spot, so the tower, its stronger waves and the Nexus are fought one by one."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 4368)


def tower_spawn(L):
    """While the tower stands, the lane's waves come out of it (just in front, on the lane side)."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 4128)


def nexus_spawn(L):
    """After the tower falls, stronger waves come out of the Nexus itself."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 5760)     # 448 in front of the Nexus: the biggest Nexus footprint reaches 320


# The FINAL BOSS (v4.0) rises in the plaza, south of the castle - every Champion's Circle is close, so a revived champion
# is back in the fight quickly. Leash: he never leaves the plaza and the lane entrances (castle = centre).
FINAL_BOSS_POS = (0, -1400)
FINAL_LEASH = 2500.0

# Hall of Champions: ONE tavern (v2.0) just north of the souls (selectors, at HALL_SOUL_DY below the centre)
HALL_TAVERNS = [(0, 160)]              # 256 x 256 footprint -> y +32..+288 inside the 384 half-size
HALL_SOUL_DY = -128


def hall_point(dx, dy):
    return (HALL_CENTRE[0] + dx, HALL_CENTRE[1] + dy)


# Hidden grove (south-east): a narrow 2-tile L-shaped passage from the plaza corner
# leads to a walled room with the Fountain of Power (HP + mana) and the two shops.
GROVE_RECTS = [
    (2048, -3328, 2304, -2304),     # passage going south from the plaza corner
    (2048, -3328, 2688, -3072),     # passage turning east
    (2688, -4224, 4352, -2688),     # the grove itself
]
GROVE_BUILDINGS = [("nfnp", 3456, -3072), ("armory", 2880, -3776), ("bank", 3456, -3776), ("apothecary", 4032, -3776)]
GROVE_ENTRANCE = (2176, -2468)


def dist_point_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


_SEGS = None


def road_distance(x, y):
    global _SEGS
    if _SEGS is None:
        _SEGS = []
        for L in range(8):
            pts = lane_waypoints(L)[:-1]          # stop at the plaza edge
            for a, b in zip(pts, pts[1:]):
                _SEGS.append((a[0], a[1], b[0], b[1]))
    return min(dist_point_seg(x, y, *s) for s in _SEGS)


# --------------------------------------------------------------------------
# The Dark Gate: a SHARED lane in the NE (lane index 8 in the script). Closed by a gate until the first player
# destroys his Nexus; then its own stronger tower + Nexus send stronger waves down an L-shaped corridor:
# north leg from the base room, east-west leg, corner room that opens into the plaza's NE corner.
# Every corridor is 1280 wide, with the same room for an army as a player's lane: spawn, then a long straight run to the first waypoint.
GATE_W = 1280
CORNER_IN, CORNER_OUT = 1664, 2944   # the corner room: its edge is one wall (256) past the lanes, it overlaps the plaza corner by 640 (the opening)
GATE_LEG_Y = 2304                    # centre line of the leg leaving the corner room


def _gate_pieces(x, y_centre):
    """A gate across a corridor running along x: two ITg3 pieces, spanning y."""
    return [("ITg3", x, y_centre - 320, 0.0), ("ITg3", x, y_centre + 320, 0.0)]


SHARED_RECTS = [
    (1664, 1664, 2944, 2944),     # corner room (overlaps the plaza corner -> the opening)
    (2944, 1664, 4480, 2944),     # east-west leg
    (3200, 2944, 4480, 4992),     # north leg
    (2944, 4992, 4736, 6144),     # base room
]
SHARED_U = 3840                   # centre line of the north leg / base
SHARED_TOWER = (SHARED_U, 3904)   # in the north leg, far in front of the Citadel (ranges don't overlap)
SHARED_NEXUS = (SHARED_U, 5568)
SHARED_TOWER_SPAWN = (SHARED_U, 3664)
SHARED_NEXUS_SPAWN = (SHARED_U, 5120)
SHARED_GATE = _gate_pieces(3008, GATE_LEG_Y)
SHARED_WAYPOINTS = [SHARED_TOWER_SPAWN, (SHARED_U, GATE_LEG_Y), (3008, GATE_LEG_Y), (2400, GATE_LEG_Y), (1500, 1500), (0, 0)]


# --------------------------------------------------------------------------
# LEVEL 3 — the Frozen Gate: second shared lane in the NW (lane 9 in the script). Closed until the Dark Citadel
# (Level 2) falls. The mirror of Level 2: corner room at the plaza's NW corner -> leg west -> leg north -> base room.
LEVEL3_RECTS = [
    (-2944, 1664, -1664, 2944),     # corner room (overlaps the plaza corner -> the opening)
    (-4480, 1664, -2944, 2944),     # leg west
    (-4480, 2944, -3200, 4992),     # leg north
    (-4736, 4992, -2944, 6144),     # base room
]
LEVEL3_U = -3840                    # centre line of the north leg / base
LEVEL3_TOWER = (LEVEL3_U, 3904)
LEVEL3_NEXUS = (LEVEL3_U, 5568)
LEVEL3_TOWER_SPAWN = (LEVEL3_U, 3664)
LEVEL3_NEXUS_SPAWN = (LEVEL3_U, 5120)
LEVEL3_GATE = _gate_pieces(-3008, GATE_LEG_Y)
LEVEL3_WAYPOINTS = [LEVEL3_TOWER_SPAWN, (LEVEL3_U, GATE_LEG_Y), (-3008, GATE_LEG_Y), (-2400, GATE_LEG_Y), (-1500, 1500), (0, 0)]


# --------------------------------------------------------------------------
# LEVEL 4 — the Shadow Gate (lane 10, SW): the point mirror of the Dark Gate. Opens when the Frozen Throne falls.
LEVEL4_RECTS = [
    (-2944, -2944, -1664, -1664),   # corner room (overlaps the plaza's SW corner -> the opening)
    (-4480, -2944, -2944, -1664),   # leg west
    (-4480, -4992, -3200, -2944),   # leg south
    (-4736, -6272, -2944, -4992),   # base room, one tile deeper: Level 5's leg leaves it
]
LEVEL4_U = -3840
LEVEL4_TOWER = (LEVEL4_U, -3904)
LEVEL4_NEXUS = (LEVEL4_U, -5632)
LEVEL4_TOWER_SPAWN = (LEVEL4_U, -3664)
LEVEL4_NEXUS_SPAWN = (LEVEL4_U, -5184)
LEVEL4_GATE = _gate_pieces(-3008, -GATE_LEG_Y)
LEVEL4_WAYPOINTS = [LEVEL4_TOWER_SPAWN, (LEVEL4_U, -GATE_LEG_Y), (-3008, -GATE_LEG_Y), (-2400, -GATE_LEG_Y), (-1500, -1500), (0, 0)]

# LEVEL 5 — the Inferno Gate (lane 11): a deeper chamber BEHIND the Level 4 base, in the far SW corner. Its monsters
# march out through the (fallen) Level 4 base and corridor. Opens when the Shadow Portal falls.
LEVEL5_RECTS = [
    (-6400, -6272, -4736, -4992),   # leg west out of the Level 4 base room
    (-7296, -6400, -6400, -4864),   # the inferno chamber
]
LEVEL5_Y = -5632
LEVEL5_TOWER = (-5600, LEVEL5_Y)
LEVEL5_NEXUS = (-6912, LEVEL5_Y)
LEVEL5_TOWER_SPAWN = (-5360, LEVEL5_Y)       # a whole army fits between here and the gate's middle post
LEVEL5_NEXUS_SPAWN = (-6464, LEVEL5_Y)
LEVEL5_GATE = _gate_pieces(-4672, LEVEL5_Y)  # in the room's first column: the army does not stand in it
LEVEL5_WAYPOINTS = [LEVEL5_TOWER_SPAWN, (LEVEL4_U, LEVEL5_Y), (LEVEL4_U, -GATE_LEG_Y), (-2400, -GATE_LEG_Y), (-1500, -1500), (0, 0)]

# lane -> (waypoints, tower, Nexus, tower spawn, Nexus spawn, gate) for the four gate lanes
GATE_GEOMETRY = {
    8: (SHARED_WAYPOINTS, SHARED_TOWER, SHARED_NEXUS, SHARED_TOWER_SPAWN, SHARED_NEXUS_SPAWN, SHARED_GATE),
    9: (LEVEL3_WAYPOINTS, LEVEL3_TOWER, LEVEL3_NEXUS, LEVEL3_TOWER_SPAWN, LEVEL3_NEXUS_SPAWN, LEVEL3_GATE),
    10: (LEVEL4_WAYPOINTS, LEVEL4_TOWER, LEVEL4_NEXUS, LEVEL4_TOWER_SPAWN, LEVEL4_NEXUS_SPAWN, LEVEL4_GATE),
    11: (LEVEL5_WAYPOINTS, LEVEL5_TOWER, LEVEL5_NEXUS, LEVEL5_TOWER_SPAWN, LEVEL5_NEXUS_SPAWN, LEVEL5_GATE),
}
