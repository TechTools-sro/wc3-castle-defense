"""Binary writers for the WarCraft III 1.27 (TFT) map files.

Every format here was checked against the official 1.27 maps shipped with the
game ((8)GardenOfWar.w3x, (12)EmeraldGardens.w3x) and a 1.27-era custom map.
"""
import struct


def _s(text):
    return text.encode("utf-8") + b"\0"


# ---------------------------------------------------------------- war3map.w3e
def write_w3e(tileset, ground_tiles, cliff_tiles, width_pts, height_pts, offset_x, offset_y, points):
    """points: list (row-major, y from bottom) of (height, water, flags, ground_idx,
    variation, cliff_idx, layer, boundary)."""
    out = bytearray()
    out += b"W3E!" + struct.pack("<i", 11) + tileset.encode()
    out += struct.pack("<i", 1)                       # custom tileset list
    out += struct.pack("<i", len(ground_tiles)) + b"".join(t.encode() for t in ground_tiles)
    out += struct.pack("<i", len(cliff_tiles)) + b"".join(t.encode() for t in cliff_tiles)
    out += struct.pack("<ii", width_pts, height_pts) + struct.pack("<ff", offset_x, offset_y)
    for (h, water, flags, g, var, cliff, layer, boundary) in points:
        w = (water & 0x3FFF) | (0x4000 if boundary else 0)
        out += struct.pack("<hh", h, w)
        out += bytes([((flags & 0xF) << 4) | (g & 0xF), var & 0xFF, ((cliff & 0xF) << 4) | (layer & 0xF)])
    return bytes(out)


# ---------------------------------------------------------------- war3map.wpm
def write_wpm(width, height, cells):
    return b"MP3W" + struct.pack("<iii", 0, width, height) + bytes(cells)


# ---------------------------------------------------------------- war3map.doo
def write_doo(trees):
    """trees: list of (id4, variation, x, y, z, angle_rad, scale, life)."""
    out = bytearray(b"W3do" + struct.pack("<iii", 8, 11, len(trees)))
    for n, (tid, var, x, y, z, ang, sc, life) in enumerate(trees):
        out += tid.encode() + struct.pack("<i7f", var, x, y, z, ang, sc, sc, sc)
        out += bytes([2, life]) + struct.pack("<ii", -1, 0) + struct.pack("<i", n)
    out += struct.pack("<ii", 0, 0)                   # special doodads: version 0, none
    return bytes(out)


# ---------------------------------------------------------------- war3map.mmp
def write_mmp(icons):
    """icons: list of (type, mx, my) with type 0=gold mine, 1=neutral bldg, 2=start loc."""
    out = bytearray(struct.pack("<ii", 0, len(icons)))
    for (t, mx, my) in icons:
        out += struct.pack("<iii", t, mx, my) + b"\xff\xff\xff\xff"
    return bytes(out)


# ---------------------------------------------------------------- war3map.w3i
def write_w3i(info):
    o = bytearray()
    o += struct.pack("<iii", 25, info["saves"], info["editor"])
    o += _s(info["name"]) + _s(info["author"]) + _s(info["description"]) + _s(info["players_rec"])
    o += struct.pack("<8f", *info["camera_bounds"])
    o += struct.pack("<4i", *info["camcomp"])
    o += struct.pack("<ii", info["play_w"], info["play_h"])
    o += struct.pack("<i", info["flags"]) + info["tileset"].encode()
    o += struct.pack("<i", -1) + _s("")                                  # loading screen: default
    o += _s(info["ls_text"]) + _s(info["ls_title"]) + _s(info["ls_subtitle"])
    o += struct.pack("<i", 0)                                            # game data set: standard
    o += _s("") + _s("") + _s("") + _s("")                               # prologue
    o += struct.pack("<i", 0) + struct.pack("<fff", 1000.0, 8000.0, 0.5) + bytes([0, 0, 0, 255])  # no fog
    o += b"\0\0\0\0" + _s("") + b"\0" + bytes([255, 255, 255, 255])     # weather, sound env, light, water tint
    o += struct.pack("<i", len(info["players"]))
    for p in info["players"]:
        o += struct.pack("<iiii", p["num"], p["type"], p["race"], p["fixed"])
        o += _s(p["name"]) + struct.pack("<ff", p["x"], p["y"]) + struct.pack("<ii", 0, 0)
    o += struct.pack("<i", len(info["forces"]))
    for f in info["forces"]:
        o += struct.pack("<ii", f["flags"], f["mask"]) + _s(f["name"])
    o += struct.pack("<i", 0)        # upgrade availability changes
    o += struct.pack("<i", 0)        # tech availability changes
    o += struct.pack("<i", 0)        # random unit tables
    o += struct.pack("<i", 0)        # random item tables
    return bytes(o)


# ---------------------------------------------------------------- war3map.w3u
VT_INT, VT_REAL, VT_UNREAL, VT_STRING = 0, 1, 2, 3


def _w3_mods(mods):
    o = bytearray(struct.pack("<i", len(mods)))
    for (fid, vt, val) in mods:
        o += fid.encode() + struct.pack("<i", vt)
        if vt == VT_INT:
            o += struct.pack("<i", int(val))
        elif vt in (VT_REAL, VT_UNREAL):
            o += struct.pack("<f", float(val))
        else:
            o += _s(val)
        o += b"\0\0\0\0"
    return bytes(o)


def write_w3u(custom_units, originals=()):
    """Object data without levels (war3map.w3u units, war3map.w3t items).
    originals: [(id, mods)] edits of standard objects; custom_units: [(base_id, new_id, mods)]."""
    o = bytearray(struct.pack("<i", 2))
    o += struct.pack("<i", len(originals))
    for oid, mods in originals:
        o += oid.encode() + b"\0\0\0\0" + _w3_mods(mods)
    o += struct.pack("<i", len(custom_units))
    for base, new, mods in custom_units:
        o += base.encode() + new.encode() + _w3_mods(mods)
    return bytes(o)


def write_w3a(originals=(), custom=()):   # also used for war3map.w3q (same level-aware layout)
    """Object data WITH levels (war3map.w3a abilities). mods: (field, var_type, level, data_pointer, value)."""
    def mods_bytes(mods):
        o = bytearray(struct.pack("<i", len(mods)))
        for (fid, vt, lvl, dp, val) in mods:
            o += fid.encode() + struct.pack("<iii", vt, lvl, dp)
            if vt == VT_INT:
                o += struct.pack("<i", int(val))
            elif vt in (VT_REAL, VT_UNREAL):
                o += struct.pack("<f", float(val))
            else:
                o += _s(val)
            o += b"\0\0\0\0"
        return bytes(o)
    o = bytearray(struct.pack("<i", 2))
    o += struct.pack("<i", len(originals))
    for oid, mods in originals:
        o += oid.encode() + b"\0\0\0\0" + mods_bytes(mods)
    o += struct.pack("<i", len(custom))
    for base, new, mods in custom:
        o += base.encode() + new.encode() + mods_bytes(mods)
    return bytes(o)


# ---------------------------------------------------------------- BLP1 (paletted)
def write_blp_paletted(img_rgb, dither=False, mips=True):
    """img_rgb: square PIL RGB image (power-of-two). Writes BLP1 paletted with an
    8-bit alpha plane and a full mipmap chain (same layout as the game's own
    UI\\MiniMap\\minimap-gold.blp)."""
    from PIL import Image
    w, h = img_rgb.size
    dmode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
    pal_img = img_rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=dmode)
    pal = pal_img.getpalette()[:768]
    pal += [0] * (768 - len(pal))
    levels = []
    lw, lh = w, h
    while True:
        if (lw, lh) == (w, h):
            p = pal_img
        else:
            p = img_rgb.resize((lw, lh), Image.Resampling.BOX).quantize(palette=pal_img, dither=dmode)
        levels.append(p.tobytes() + b"\xff" * (lw * lh))
        if (lw == 1 and lh == 1) or not mips:
            break
        lw, lh = max(1, lw // 2), max(1, lh // 2)
    header_size = 4 + 6 * 4 + 64 + 64        # magic + 6 ints + 16 mip offsets + 16 mip sizes = 156
    offset = header_size + 1024
    offsets, sizes = [], []
    for lv in levels:
        offsets.append(offset)
        sizes.append(len(lv))
        offset += len(lv)
    offsets += [0] * (16 - len(offsets))
    sizes += [0] * (16 - len(sizes))
    o = bytearray(b"BLP1" + struct.pack("<6I", 1, 8, w, h, 4, 1 if mips else 0))
    o += struct.pack("<16I", *offsets) + struct.pack("<16I", *sizes)
    for i in range(256):
        r, g, b = pal[3 * i], pal[3 * i + 1], pal[3 * i + 2]
        o += bytes([b, g, r, 0])
    for lv in levels:
        o += lv
    return bytes(o)
