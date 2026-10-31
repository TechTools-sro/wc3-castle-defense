"""Shop button icons for Strength / Agility / Intelligence, cut from the game's own hero-attribute icons
(UI\\Widgets\\Console\\Human\\infocard-heroattributes-*.blp, 64x64 paletted with a gold frame).
The frame is cropped off so they look like normal command buttons; a greyed DISBTN copy goes with each."""
import struct

from PIL import Image, ImageEnhance, ImageOps

from objects import STAT_ICON
from w3files import write_blp_paletted

SRC = "UI\\Widgets\\Console\\Human\\infocard-heroattributes-{}.blp"


def _read_blp_paletted(d):
    comp, abits, w, h = struct.unpack("<4I", d[4:20])
    off = struct.unpack("<I", d[28:32])[0]
    pal = d[156:156 + 1024]
    idx, al = d[off:off + w * h], d[off + w * h:off + 2 * w * h]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for i in range(w * h):
        b, g, r, _ = pal[idx[i] * 4:idx[i] * 4 + 4]
        px[i % w, i // w] = (r, g, b)
    return img


def stat_icons(game):
    """game: tools/mpq.GameData -> {archive path: BLP bytes}."""
    out = {}
    for key, path in STAT_ICON.items():
        src = _read_blp_paletted(game.read(SRC.format(key)))
        btn = src.crop((4, 4, 52, 52))      # inside the gold frame (frame at 1-2 and 53-54)
        btn = btn.resize((64, 64), Image.Resampling.LANCZOS)
        dis = ImageEnhance.Brightness(ImageOps.grayscale(btn).convert("RGB")).enhance(0.55)
        out[path] = write_blp_paletted(btn)
        out[path.replace("CommandButtons\\BTN", "CommandButtonsDisabled\\DISBTN")] = write_blp_paletted(dis)
    return out
