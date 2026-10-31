"""TechTools-style splash art: replaces WarCraft III's multiplayer loading screen and adds a lobby preview.

Brand (techtools-brain/brand): dark navy (#070a12 / #0f1a34) with a radial blue glow, the blue double-T
mark, white Inter 900 wordmark, blues #2173d8 / #1e9bf6 / #4f87cf, accent cyan #11b6c8, text #eef4ff.

The default multiplayer loading screen is 4 tiles (top: 512x512, bottom: 512x256) at
UI\\Glues\\Loading\\Multiplayer\\Loading-{TopLeft,Human-TopRight,BotLeft,Human-BotRight}.blp - importing
files at those paths into the map replaces them (same trick as Legion TD). Players are fixed Human, so
the Human tiles are the ones shown. The game draws the map title, preview and player list over the left
half, so the brand art lives on the right.
"""
import base64
import io
import math
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BRAND = os.path.expanduser("~/projects/techtools-brain/brand")
NAVY, NAVY2 = (7, 10, 18), (15, 26, 52)
BLUE, BLUE2, BLUE3, CYAN, WHITE = (33, 115, 216), (30, 155, 246), (79, 135, 207), (17, 182, 200), (238, 244, 255)


def _inter(weight, size):
    css = os.path.join(BRAND, "social", "youtube-banner-src", "fonts.css")
    try:
        text = open(css).read()
        m = re.search(r"font-weight:%d;[^}]*?base64,([A-Za-z0-9+/=]+)" % weight, text)
        if m:
            font = ImageFont.truetype(io.BytesIO(base64.b64decode(m.group(1))), size)
            try:                      # the brand Inter is a variable font: pick the weight axis
                font.set_variation_by_axes([weight])
            except Exception:
                pass
            return font
    except Exception:
        pass
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _glow(w, h, cx, cy, r, color, strength):
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    px = layer.load()
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy) / r
            k = max(0.0, 1.0 - d) ** 2 * strength
            px[x, y] = tuple(int(c * k) for c in color)
    return layer


def _castle(draw, x0, base, scale, color):
    """Simple castle silhouette (towers with battlements) for flavour."""
    def tower(cx, w, h):
        draw.rectangle([cx - w // 2, base - h, cx + w // 2, base], fill=color)
        m = w // 5
        for i in range(3):
            bx = cx - w // 2 + i * 2 * m
            draw.rectangle([bx, base - h - m, bx + m, base - h], fill=color)
    s = scale
    tower(x0 + int(60 * s), int(70 * s), int(210 * s))
    tower(x0 + int(360 * s), int(70 * s), int(210 * s))
    draw.rectangle([x0 + int(60 * s), base - int(120 * s), x0 + int(360 * s), base], fill=color)
    tower(x0 + int(210 * s), int(110 * s), int(300 * s))
    for i in range(9):
        bx = x0 + int((95 + i * 30) * s)
        draw.rectangle([bx, base - int(140 * s), bx + int(14 * s), base - int(120 * s)], fill=color)
    draw.pieslice([x0 + int(180 * s), base - int(80 * s), x0 + int(240 * s), base - int(20 * s) + int(60 * s)],
                  180, 360, fill=NAVY)


def render():
    """Loading screen - deliberately minimal: flat dark navy + the title block on the far right.
    WarCraft stretches this 4:3 image over a 16:9 screen and draws its own map title / preview / player list
    over the left ~62% and the loading bar at the bottom, so the art is laid out on a 16:9 canvas (true
    proportions on screen) right of the player list, then squeezed to 1024x768. The background is FLAT on
    purpose: the 4 tiles are filtered separately, and any colour change across a tile edge shows as a seam."""
    W, H = 1366, 768
    img = Image.new("RGB", (W, H), (8, 14, 30))
    cx, maxw = 1112, 400          # screen x ~1235..1890 at 1920 wide; the player list ends at ~1190
    mark = Image.open(os.path.join(BRAND, "social", "youtube-banner-src", "mark.png")).convert("RGBA")
    mk = mark.resize((int(150 * mark.width / mark.height), 150), Image.Resampling.LANCZOS)
    img.paste(mk, (cx - mk.width // 2, 170), mk)
    d = ImageDraw.Draw(img)

    def fit(text, font_fn, size, width):
        while size > 20 and d.textlength(text, font=font_fn(size)) > width:
            size -= 2
        return font_fn(size)

    _fancy_text(img, "TECHTOOLS", fit("TECHTOOLS", lambda s: _inter(900, s), 56, maxw - 60), cx, 345,
                (210, 238, 255), BLUE2, BLUE, (6, 14, 34), 4, shadow=6)
    _fancy_text(img, "CASTLE DEFENCE", fit("CASTLE DEFENCE", _serif, 64, maxw), cx, 420,
                GOLD_TOP, GOLD_MID, GOLD_BOT, (40, 18, 4), 6, shadow=8)
    d = ImageDraw.Draw(img)
    d.line([(cx - 150, 530), (cx + 150, 530)], fill=(60, 100, 170), width=2)
    tag = "Pick a champion  \u00b7  Hold your lane"
    f = fit(tag, lambda s: _inter(600, s), 22, maxw)
    d.text((cx - d.textlength(tag, font=f) / 2, 546), tag, font=f, fill=(170, 195, 235))
    return img.resize((1024, 768), Image.Resampling.LANCZOS)


def _add(base, glow):
    from PIL import ImageChops
    return ImageChops.add(base, glow)


def loading_tiles(img):
    """-> {archive path: PIL image} for the 4 multiplayer loading-screen tiles."""
    p = "UI\\Glues\\Loading\\Multiplayer\\Loading-"
    small = img.resize((512, 384), Image.Resampling.LANCZOS)     # low-res on purpose: keeps the map small
    return {
        p + "TopLeft.blp": small.crop((0, 0, 256, 256)),
        p + "Human-TopRight.blp": small.crop((256, 0, 512, 256)),
        p + "BotLeft.blp": small.crop((0, 256, 256, 384)),
        p + "Human-BotRight.blp": small.crop((256, 256, 512, 384)),
    }


def _vgrad(w, h, top, bottom):
    g = Image.linear_gradient("L").resize((w, h))
    return Image.composite(Image.new("RGB", (w, h), bottom), Image.new("RGB", (w, h), top), g)


GOLD_TOP, GOLD_MID, GOLD_BOT = (255, 244, 170), (240, 180, 50), (150, 85, 15)
SERIF = "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Black.ttf"


def _serif(size):
    try:
        return ImageFont.truetype(SERIF, size)
    except Exception:
        return _inter(900, size)


def _grad3(w, h, top, mid, bot):
    """Vertical 3-stop gradient image."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.5:
            a, b, k = top, mid, t / 0.5
        else:
            a, b, k = mid, bot, (t - 0.5) / 0.5
        c = tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def _fancy_text(img, text, font, cx, y, fill_top, fill_mid, fill_bot, outline, stroke, shadow=10):
    """WarCraft-style text: gradient fill, dark outline, soft drop shadow, centred on cx."""
    d = ImageDraw.Draw(img)
    l, t, r, b = d.textbbox((0, 0), text, font=font, stroke_width=stroke)
    w, h = r - l, b - t
    x = int(cx - w / 2) - l
    # shadow
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).text((x + shadow // 2, y + shadow), text, font=font, fill=200, stroke_width=stroke, stroke_fill=200)
    sh = sh.filter(ImageFilter.GaussianBlur(shadow))
    img.paste(Image.new("RGB", img.size, (0, 0, 0)), (0, 0), sh)
    # outline
    ImageDraw.Draw(img).text((x, y), text, font=font, fill=outline, stroke_width=stroke, stroke_fill=outline)
    # gradient fill
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).text((x, y), text, font=font, fill=255)
    grad = _grad3(img.size[0], h + 4, fill_top, fill_mid, fill_bot)
    full = Image.new("RGB", img.size, fill_mid)
    full.paste(grad, (0, y + t - 2))
    img.paste(full, (0, 0), m)
    # thin bright inner highlight on the upper edge
    hi = m.filter(ImageFilter.GaussianBlur(1)).point(lambda v: 60 if v > 128 else 0)
    shifted = Image.new("L", img.size, 0)
    shifted.paste(hi, (0, -2))
    img.paste(Image.new("RGB", img.size, (255, 255, 255)), (0, 0), Image.composite(Image.new("L", img.size, 0), shifted, m.point(lambda v: 255 - v)) if False else Image.new("L", img.size, 0))


def _castle_mask(S, cx, base):
    mask = Image.new("L", (S, S), 0)
    m = ImageDraw.Draw(mask)

    def battlements(x1, x2, top, n, h):
        w = (x2 - x1) / (2 * n - 1)
        for i in range(n):
            m.rectangle([x1 + 2 * i * w, top - h, x1 + (2 * i + 1) * w, top], fill=255)

    m.rectangle([180, 560, 844, base], fill=255)                 # curtain wall
    battlements(180, 844, 560, 11, 40)
    for tx in (215, 809):                                        # side towers
        m.rectangle([tx - 80, 430, tx + 80, base], fill=255)
        battlements(tx - 80, tx + 80, 430, 3, 46)
        m.polygon([(tx - 92, 384), (tx + 92, 384), (tx, 270)], fill=255)   # pointed roofs
    m.rectangle([cx - 125, 330, cx + 125, base], fill=255)       # keep
    battlements(cx - 125, cx + 125, 330, 4, 52)
    m.rectangle([cx - 4, 178, cx + 4, 278], fill=255)            # flag pole
    return mask


_LAST_CASTLE_SCENE = None


def castle_scene():
    """The stone castle (bg + castle + glows) at 1024, as drawn for the icon."""
    if _LAST_CASTLE_SCENE is None:
        render_icon()
    return _LAST_CASTLE_SCENE


def _monster_mask(S, x, base, sc, facing, weapon):
    """Undead attacker silhouette (L mask) standing at (x, base), facing +1 = right / -1 = left.
    Unit space: 100 = roughly the monster's height. Returns (mask, eye position)."""
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)

    def P(px, py):
        return (x + facing * px * sc, base + py * sc)

    def w(v):
        return max(1, int(v * sc))

    def disc(px, py, r):
        cx, cy = P(px, py)
        d.ellipse([cx - r * sc, cy - r * sc, cx + r * sc, cy + r * sc], fill=255)

    d.line([P(-6, -44), P(-15, -22), P(-26, 0)], fill=255, width=w(10), joint="curve")    # back leg
    d.line([P(6, -44), P(20, -24), P(16, 0)], fill=255, width=w(10), joint="curve")       # front leg
    disc(-26, 0, 6)
    disc(18, 0, 6)
    d.polygon([P(-15, -38), P(11, -38), P(28, -72), P(8, -90), P(-13, -70)], fill=255)    # hunched torso
    disc(28, -88, 12)                                                                     # head
    d.polygon([P(21, -96), P(9, -118), P(28, -99)], fill=255)                             # horns
    d.polygon([P(31, -97), P(40, -120), P(37, -93)], fill=255)
    if weapon == "axe":                                                                   # raised axe
        d.line([P(14, -78), P(28, -100), P(32, -112)], fill=255, width=w(9), joint="curve")
        d.line([P(22, -90), P(50, -146)], fill=255, width=w(6))
        d.polygon([P(40, -156), P(66, -160), P(72, -134), P(48, -128)], fill=255)
    else:                                                                                 # spear thrust
        d.line([P(12, -76), P(36, -72)], fill=255, width=w(9))
        d.line([P(-14, -64), P(78, -82)], fill=255, width=w(5))
        d.polygon([P(74, -90), P(96, -84), P(76, -74)], fill=255)
    d.line([P(4, -76), P(24, -60), P(40, -58)], fill=255, width=w(8), joint="curve")    # clawed arm
    for cy in (-64, -58, -52):
        d.line([P(40, -58), P(52, cy)], fill=255, width=w(3))
    return m, P(33, -90)


def _draw_monsters(img, S, base, specs):
    """specs: [(x, base offset, scale, facing, weapon)] drawn back to front: red rim glow, dark body, red eyes."""
    img = img.convert("RGB")
    for (x, dy, sc, facing, weapon) in specs:
        b = base + dy
        m, (ex, ey) = _monster_mask(S, x, b, sc, facing, weapon)
        sh = Image.new("L", (S, S), 0)
        ImageDraw.Draw(sh).ellipse([x - 40 * sc, b - 6 * sc, x + 40 * sc, b + 6 * sc], fill=150)
        img.paste((4, 4, 8), (0, 0), sh.filter(ImageFilter.GaussianBlur(4)))
        halo = m.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.8))
        img = Image.composite(Image.new("RGB", (S, S), (190, 40, 25)), img, halo)
        img.paste((120, 24, 18), (0, 0), m.filter(ImageFilter.MaxFilter(5)))
        img.paste((22, 12, 26), (0, 0), m)
        eg = Image.new("RGB", (S, S), (0, 0, 0))
        r = 4 * sc
        ImageDraw.Draw(eg).ellipse([ex - 3 * r, ey - 3 * r, ex + 3 * r, ey + 3 * r], fill=(255, 60, 20))
        img = _add(img, eg.filter(ImageFilter.GaussianBlur(6 * sc)))
        ImageDraw.Draw(img).ellipse([ex - r, ey - r, ex + r, ey + r], fill=(255, 210, 120))
    return img


def render_icon():
    """Map icon: TechTools logo on top, big stone castle, CASTLE DEFENCE in WarCraft gold. 1024 -> 256."""
    S, cx, base = 1024, 512, 830
    img = _vgrad(S, S, (10, 16, 36), (4, 6, 12))
    img = _add(img, _glow(S // 4, S // 4, S // 8, 500 // 4, 460 // 4, BLUE, 0.75).resize((S, S), Image.Resampling.BILINEAR))
    img = _add(img, _glow(S // 4, S // 4, S // 8, 840 // 4, 300 // 4, (200, 90, 10), 0.35).resize((S, S), Image.Resampling.BILINEAR))

    # --- stone castle ---
    mask = _castle_mask(S, cx, base)
    stone = _grad3(S, S, (150, 160, 178), (98, 106, 124), (46, 50, 62))
    sd = ImageDraw.Draw(stone)
    for yy in range(180, base, 34):                               # brick courses
        sd.line([(0, yy), (S, yy)], fill=(58, 62, 74), width=3)
        off = 0 if (yy // 34) % 2 else 34
        for xx in range(off, S, 68):
            sd.line([(xx, yy), (xx, yy + 34)], fill=(64, 68, 80), width=3)
    outline = mask.filter(ImageFilter.MaxFilter(9))
    img.paste(Image.new("RGB", (S, S), (12, 14, 22)), (0, 0), outline)       # dark outline
    img.paste(stone, (0, 0), mask)
    # roofs + flag in TechTools blue
    d = ImageDraw.Draw(img)
    for tx in (215, 809):
        d.polygon([(tx - 92, 384), (tx + 92, 384), (tx, 270)], fill=BLUE)
        d.polygon([(tx, 270), (tx + 92, 384), (tx + 10, 384)], fill=(22, 90, 180))
    d.polygon([(cx + 4, 180), (cx + 104, 206), (cx + 4, 232)], fill=BLUE2)
    # glowing blue windows (TechTools light)
    glow = Image.new("RGB", (S, S), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    wins = [(cx - 70, 400), (cx + 34, 400), (215 - 18, 470), (809 - 18, 470), (cx - 18, 500)]
    for (wx, wy) in wins:
        gd.rounded_rectangle([wx - 10, wy - 10, wx + 46, wy + 76], 12, fill=(30, 120, 255))
    img = _add(img, glow.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    for (wx, wy) in wins:
        d.rounded_rectangle([wx, wy, wx + 36, wy + 66], 16, fill=(120, 200, 255))
        d.rectangle([wx + 16, wy, wx + 20, wy + 66], fill=(40, 90, 170))
    # torch-lit gate (WarCraft warm light)
    gl = Image.new("RGB", (S, S), (0, 0, 0))
    ImageDraw.Draw(gl).ellipse([cx - 150, 650, cx + 150, 900], fill=(255, 140, 30))
    img = _add(img, gl.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.6)))
    d = ImageDraw.Draw(img)
    d.rectangle([cx - 66, 720, cx + 66, base], fill=(20, 10, 6))
    d.pieslice([cx - 66, 654, cx + 66, 786], 180, 360, fill=(20, 10, 6))
    for gx in range(cx - 50, cx + 60, 26):                         # portcullis
        d.line([(gx, 680), (gx, base)], fill=(110, 70, 30), width=5)
    for tx in (cx - 100, cx + 100):                                 # torches
        d.rectangle([tx - 5, 700, tx + 5, 760], fill=(80, 50, 20))
        d.ellipse([tx - 14, 672, tx + 14, 704], fill=(255, 200, 80))
    d.rectangle([90, base, S - 90, base + 10], fill=(40, 44, 56))

    global _LAST_CASTLE_SCENE
    _LAST_CASTLE_SCENE = img.copy()
    # --- shrink the castle scene so the gold title fits below it ---
    final = _vgrad(S, S, (10, 16, 36), (4, 6, 12))
    final = _add(final, _glow(S // 4, S // 4, S // 8, 420 // 4, 460 // 4, BLUE, 0.75).resize((S, S), Image.Resampling.BILINEAR))
    k = 0.64                                       # castle scale; leaves room for the attackers on both sides
    top = 110                                      # margin above the flag so the top edge can fade out too
    crop = img.crop((0, top, S, 852))
    cw, ch = int(S * k), int((852 - top) * k)
    crop = crop.resize((cw, ch), Image.Resampling.LANCZOS)
    feather = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(feather).rectangle([24, 24, cw - 24, ch - 6], fill=255)
    feather = feather.filter(ImageFilter.GaussianBlur(16))
    ground = 682                                   # castle base line in the final icon
    final.paste(crop, ((S - cw) // 2, ground - int((830 - top) * k)), feather)
    # undead attackers closing in from left and right (back to front)
    img = _draw_monsters(final, S, ground, [
        (42, -34, 1.05, 1, "spear"), (S - 42, -34, 1.05, -1, "spear"),
        (118, -14, 1.35, 1, "axe"), (S - 118, -14, 1.35, -1, "axe"),
        (196, 0, 1.75, 1, "axe"), (S - 196, 0, 1.75, -1, "spear"),
    ])

    # --- TechTools lockup on top ---
    mark = Image.open(os.path.join(BRAND, "social", "youtube-banner-src", "mark.png")).convert("RGBA")
    mh = 104
    mk = mark.resize((int(mh * mark.width / mark.height), mh), Image.Resampling.LANCZOS)
    tfont = _inter(900, 92)
    tw = ImageDraw.Draw(img).textlength("TECHTOOLS", font=tfont)
    gap = 26
    x0 = int((S - (mk.width + gap + tw)) / 2)
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    halo.paste(mk, (x0, 40), mk)
    img = Image.alpha_composite(img.convert("RGBA"), halo.filter(ImageFilter.GaussianBlur(10))).convert("RGB")
    img.paste(mk, (x0, 40), mk)
    _fancy_text(img, "TECHTOOLS", tfont, x0 + mk.width + gap + tw / 2, 42, (200, 235, 255), BLUE2, BLUE, (6, 14, 34), 6, shadow=8)

    # --- CASTLE DEFENCE in WarCraft gold ---
    _fancy_text(img, "CASTLE", _serif(132), cx, 690, GOLD_TOP, GOLD_MID, GOLD_BOT, (40, 18, 4), 9)
    _fancy_text(img, "DEFENCE", _serif(104), cx, 832, GOLD_TOP, GOLD_MID, GOLD_BOT, (40, 18, 4), 8)
    return img


def preview_tga(img=None):
    """256x256 uncompressed 32-bit TGA for the lobby / loading screen box (war3mapPreview.tga)."""
    sq = render_icon().resize((256, 256), Image.Resampling.LANCZOS).convert("RGB")
    out = io.BytesIO()
    sq.save(out, format="TGA")
    return out.getvalue()
