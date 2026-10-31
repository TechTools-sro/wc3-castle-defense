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

MAP_TILES = 96
HALF = MAP_TILES * 128 // 2            # 6144
CAMCOMP = (6, 6, 4, 8)                 # boundary tiles: left, right, bottom, top (WE default)
PLAY_MINX = -HALF + CAMCOMP[0] * 128   # -5376
PLAY_MAXX = HALF - CAMCOMP[1] * 128    # 5376
PLAY_MINY = -HALF + CAMCOMP[2] * 128   # -5632
PLAY_MAXY = HALF - CAMCOMP[3] * 128    # 5120

PLAZA = 1536                           # plaza = |x|,|y| <= PLAZA (all bounds on the 128 grid)
LANE_IN, LANE_OUT = 384, 1024          # lane corridor spans |u| in [LANE_IN, LANE_OUT] (640 = gate width)
LANE_END = 3968                        # lanes run v in [PLAZA, LANE_END]
BASE_START, BASE_END = 3968, 4864      # each lane ends in its OWN enemy base room
ROOM_IN, ROOM_OUT = 256, 1152           # base room spans |u| in [ROOM_IN, ROOM_OUT]; |u| < ROOM_IN stays a wall

HALL_CENTRE = (-3200, 3200)            # Hall of Champions (champion select), in the NW void
HALL_HALF = 768

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
    for (x0, y0, x1, y1) in SHARED_RECTS:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return ("shared", -1)
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
LANE_WAYPOINTS_ARM = [      # (|u| * side, v); the last point is the castle
    (LANE_U, 3880),         # 0 spawn (tower; the script switches to the Nexus once the tower falls)
    (LANE_U, 3500),         # 1 top of the lane
    (LANE_U, 2700),         # 2
    (LANE_U, 1900),         # 3 bottom of the lane
    (LANE_U, 1000),         # 4 plaza
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
    return from_arm(d, s * LANE_U, 4544)


def tower_pos(L):
    """The lane's own strong enemy tower, centred right in front of its Nexus."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 4096)


def tower_spawn(L):
    """While the tower stands, the lane's waves come out of it (just in front, on the lane side)."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 3880)


def nexus_spawn(L):
    """After the tower falls, stronger waves come out of the Nexus itself."""
    d, s = L // 2, lane_side(L)
    return from_arm(d, s * LANE_U, 4230)


# Hall of Champions: taverns in a ring, the souls (selectors) in the middle.
# five halls in a tight ring (radius 420) around the souls in the middle
HALL_TAVERNS = [(0, 420), (399, 130), (247, -340), (-247, -340), (-399, 130)]


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
SHARED_TOWER = (SHARED_U, 4032)
SHARED_NEXUS = (SHARED_U, 4544)
SHARED_TOWER_SPAWN = (SHARED_U, 3700)
SHARED_NEXUS_SPAWN = (SHARED_U, 4290)
SHARED_GATE = ("ITg3", 1984, 1600, 0.0)      # spans y 1280..1920 = the leg width
SHARED_WAYPOINTS = [SHARED_TOWER_SPAWN, (SHARED_U, 2600), (SHARED_U, 1600), (2300, 1600), (1450, 1450), (0, 0)]
