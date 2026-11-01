"""Map geometry for "TechTools Castle Defence" (hero lane defense).

96x96 map (compact: short lanes that start right at the castle). The castle sits in the centre plaza. Four fronts (N, E, S, W) run
outward; each front is two walled lanes (left/right) that meet in front of the
enemy base at the far end. Every lane belongs to one player's champion:
4 fronts x 2 lanes = 8 players. Everything that is not a lane, the plaza, a base
or the Hall of Champions is abyss (unwalkable void).

Arm-local coordinates: u = across the arm, v = outward from the castle.
Arm d: 0=North, 1=East, 2=South, 3=West (clockwise rotation of the North arm).
Lane L = 2*d + side; side 0 = left (u<0), 1 = right (u>0). Lane L = Player(L).
"""

MAP_TILES = 112                        # was 96: lanes got 1024 longer so the tower sits well away from the circle
HALF = MAP_TILES * 128 // 2            # 7168
CAMCOMP = (6, 6, 4, 8)                 # boundary tiles: left, right, bottom, top (WE default)
PLAY_MINX = -HALF + CAMCOMP[0] * 128   # -6400
PLAY_MAXX = HALF - CAMCOMP[1] * 128    # 6400
PLAY_MINY = -HALF + CAMCOMP[2] * 128   # -6656
PLAY_MAXY = HALF - CAMCOMP[3] * 128    # 6144

PLAZA = 1536                           # plaza = |x|,|y| <= PLAZA (all bounds on the 128 grid)
LANE_IN, LANE_OUT = 384, 1024          # lane corridor spans |u| in [LANE_IN, LANE_OUT] (640 = gate width)
LANE_END = 4992                        # lanes run v in [PLAZA, LANE_END]
BASE_START, BASE_END = 4992, 5888      # each lane ends in its OWN enemy base room
ROOM_IN, ROOM_OUT = 256, 1152           # base room spans |u| in [ROOM_IN, ROOM_OUT]; |u| < ROOM_IN stays a wall

# Hall of Champions (champion select): v3.8 (Jiri) a SMALL room in the empty top-right (NE) corner, far from every
# spawn point. The old 1536-wide hall in the NW lay 512 from the Frozen Gate tower spawn, and a big wave that did not
# fit there was placed by the engine onto the nearest free floor = into the hall (CreateUnit ignores walls).
HALL_CENTRE = (5632, 5504)             # inside the camera bounds (margins: 4 cells left/right, 2 top/bottom)
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


LANE_U = 704
LANE_WAYPOINTS_ARM = [      # (|u| * side, v); the last point is the castle. Point 1 lies BELOW the tower spawn
    (LANE_U, 3360),         # 0 spawn (tower; the script switches to the Nexus once the tower falls)
    (LANE_U, 2800),         # 1
    (LANE_U, 2100),         # 2
    (LANE_U, 1300),         # 3 plaza edge
    (LANE_U, 700),          # 4 plaza
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
    """Icecrown gate across the lane entrance: (destructable id, x, y, facing). 640x128 footprint
    (Gate1Path 20x4 cells) = exactly the lane width. ITg1 (facing 270) spans x, ITg3 (facing 0) spans y."""
    d, s = L // 2, lane_side(L)
    x, y = from_arm(d, s * LANE_U, PLAZA + 64)
    return ("ITg1", x, y, 270.0) if d % 2 == 0 else ("ITg3", x, y, 0.0)


def lane_label(L):
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, PLAZA + 420)


def nexus_pos(L):
    """The lane's own enemy Nexus (spawns the waves of this lane, its boss rises from it)."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 5440)


def tower_pos(L):
    """The lane's own strong enemy tower, in the lane centre far in front of its Nexus: tower (range 750) and
    Nexus (range 700, measured from its big footprint) never cover the same spot, so the tower, its stronger waves and the Nexus are fought one by one."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 3600)


def tower_spawn(L):
    """While the tower stands, the lane's waves come out of it (just in front, on the lane side)."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 3360)


def nexus_spawn(L):
    """After the tower falls, stronger waves come out of the Nexus itself."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 5120)


# The FINAL BOSS (v4.0) rises in the plaza, south of the castle - every Champion's Circle is close, so a revived champion
# is back in the fight quickly. Leash: he never leaves the plaza and the lane entrances (castle = centre).
FINAL_BOSS_POS = (0, -1000)
FINAL_LEASH = 1700.0

# Hall of Champions: ONE tavern (v2.0) just north of the souls (selectors, at HALL_SOUL_DY below the centre)
HALL_TAVERNS = [(0, 160)]              # 256 x 256 footprint -> y +32..+288 inside the 384 half-size
HALL_SOUL_DY = -128


def hall_point(dx, dy):
    return (HALL_CENTRE[0] + dx, HALL_CENTRE[1] + dy)


# Hidden grove (south-east): a narrow 2-tile L-shaped passage from the plaza corner
# leads to a walled room with the Fountain of Power (HP + mana) and the two shops.
GROVE_RECTS = [
    (1280, -2560, 1536, -1536),     # passage going south from the plaza corner
    (1280, -2560, 1920, -2304),     # passage turning east
    (1920, -3456, 3584, -1920),     # the grove itself
]
GROVE_BUILDINGS = [("nfnp", 2688, -2304), ("armory", 2112, -3008), ("bank", 2688, -3008), ("apothecary", 3264, -3008)]
GROVE_ENTRANCE = (1408, -1700)


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
SHARED_RECTS = [
    (1280, 1280, 1920, 1920),     # corner room (overlaps the plaza corner -> the opening)
    (1920, 1280, 3840, 1920),     # east-west leg
    (3200, 1920, 3840, 3840),     # north leg
    (2944, 3840, 4096, 4864),     # base room
]
SHARED_U = 3520                   # centre line of the north leg / base
SHARED_TOWER = (SHARED_U, 2900)   # in the north leg, far in front of the Citadel (ranges don't overlap)
SHARED_NEXUS = (SHARED_U, 4544)
SHARED_TOWER_SPAWN = (SHARED_U, 2660)
SHARED_NEXUS_SPAWN = (SHARED_U, 4290)
SHARED_GATE = ("ITg3", 1984, 1600, 0.0)      # spans y 1280..1920 = the leg width
SHARED_WAYPOINTS = [SHARED_TOWER_SPAWN, (SHARED_U, 2400), (SHARED_U, 1600), (2300, 1600), (1450, 1450), (0, 0)]


# --------------------------------------------------------------------------
# LEVEL 3 — the Frozen Gate: second shared lane in the NW (lane 9 in the script). Closed until the Dark Citadel
# (Level 2) falls. The corridor runs around the void where the Hall of Champions stood until v3.7: corner room at the
# plaza's NW corner -> leg west -> leg north -> base room in the top-left corner.
LEVEL3_RECTS = [
    (-2048, 1280, -1280, 2048),     # corner room (overlaps the plaza corner -> the opening)
    (-5120, 1408, -2048, 2048),     # leg west (under the Hall, above the West lanes' base rooms)
    (-5120, 2048, -4480, 3968),     # leg north (left of the Hall)
    (-5248, 3968, -4352, 4864),     # base room
]
LEVEL3_U = -4800                    # centre line of the north leg / base
LEVEL3_TOWER = (LEVEL3_U, 2900)
LEVEL3_NEXUS = (LEVEL3_U, 4416)
LEVEL3_TOWER_SPAWN = (LEVEL3_U, 2660)
LEVEL3_NEXUS_SPAWN = (LEVEL3_U, 4100)
LEVEL3_GATE = ("ITg3", -2112, 1728, 0.0)     # spans y 1408..2048 = the west leg
LEVEL3_WAYPOINTS = [LEVEL3_TOWER_SPAWN, (LEVEL3_U, 2300), (LEVEL3_U, 1728), (-3200, 1728), (-1700, 1650), (0, 0)]


# --------------------------------------------------------------------------
# LEVEL 4 — the Shadow Gate (lane 10, SW): the point mirror of the Dark Gate. Opens when the Frozen Throne falls.
LEVEL4_RECTS = [
    (-1920, -1920, -1280, -1280),   # corner room (overlaps the plaza's SW corner -> the opening)
    (-3840, -1920, -1920, -1280),   # leg west
    (-3840, -3840, -3200, -1920),   # leg south
    (-4096, -4864, -2944, -3840),   # base room
]
LEVEL4_U = -3520
LEVEL4_TOWER = (LEVEL4_U, -2900)
LEVEL4_NEXUS = (LEVEL4_U, -4544)
LEVEL4_TOWER_SPAWN = (LEVEL4_U, -2660)
LEVEL4_NEXUS_SPAWN = (LEVEL4_U, -4290)
LEVEL4_GATE = ("ITg3", -1984, -1600, 0.0)    # spans y -1920..-1280
LEVEL4_WAYPOINTS = [LEVEL4_TOWER_SPAWN, (LEVEL4_U, -2400), (LEVEL4_U, -1600), (-2300, -1600), (-1450, -1450), (0, 0)]

# LEVEL 5 — the Inferno Gate (lane 11): a deeper chamber BEHIND the Level 4 base, in the far SW corner. Its monsters
# march out through the (fallen) Level 4 base and corridor. Opens when the Shadow Portal falls.
LEVEL5_RECTS = [
    (-5376, -4672, -4096, -4032),   # leg west out of the Level 4 base room
    (-6272, -4864, -5376, -3840),   # the inferno chamber
]
LEVEL5_Y = -4352
LEVEL5_TOWER = (-4650, LEVEL5_Y)
LEVEL5_NEXUS = (-5824, LEVEL5_Y)
LEVEL5_TOWER_SPAWN = (-4400, LEVEL5_Y)
LEVEL5_NEXUS_SPAWN = (-5300, LEVEL5_Y)
LEVEL5_GATE = ("ITg3", -4160, LEVEL5_Y, 0.0)  # spans y -4672..-4032 (the leg)
LEVEL5_WAYPOINTS = [LEVEL5_TOWER_SPAWN, (LEVEL4_U, LEVEL5_Y), (LEVEL4_U, -1600), (-2300, -1600), (-1450, -1450), (0, 0)]

# lane -> (waypoints, tower, Nexus, tower spawn, Nexus spawn, gate) for the four gate lanes
GATE_GEOMETRY = {
    8: (SHARED_WAYPOINTS, SHARED_TOWER, SHARED_NEXUS, SHARED_TOWER_SPAWN, SHARED_NEXUS_SPAWN, SHARED_GATE),
    9: (LEVEL3_WAYPOINTS, LEVEL3_TOWER, LEVEL3_NEXUS, LEVEL3_TOWER_SPAWN, LEVEL3_NEXUS_SPAWN, LEVEL3_GATE),
    10: (LEVEL4_WAYPOINTS, LEVEL4_TOWER, LEVEL4_NEXUS, LEVEL4_TOWER_SPAWN, LEVEL4_NEXUS_SPAWN, LEVEL4_GATE),
    11: (LEVEL5_WAYPOINTS, LEVEL5_TOWER, LEVEL5_NEXUS, LEVEL5_TOWER_SPAWN, LEVEL5_NEXUS_SPAWN, LEVEL5_GATE),
}
