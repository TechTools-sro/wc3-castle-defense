"""Re-read a built .w3x, sanity-check every file and render a top-down preview PNG."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gen'))
from mpq import Archive
import w3i as W3I
import layout as LY
from PIL import Image, ImageDraw

path, out_png = sys.argv[1], sys.argv[2]
a = Archive(path)
print('files:', a.read('(listfile)').decode().split())
i = W3I.parse(a.read('war3map.w3i'))
print('w3i ok', i['consumed'], '/', i['total'], i['flags'], i['tileset'], len(i['players']), 'players')
e = a.read('war3map.w3e')
n, = struct.unpack_from('<i', e, 13); p = 17; ground = [e[p+4*k:p+4*k+4].decode() for k in range(n)]; p += 4*n
n2, = struct.unpack_from('<i', e, p); p += 4 + 4*n2
w, h = struct.unpack_from('<ii', e, p); p += 16
assert len(e) == p + 7*w*h
wpm = a.read('war3map.wpm'); pw, ph = struct.unpack_from('<ii', wpm, 8); assert len(wpm) == 16 + pw*ph
doo = a.read('war3map.doo'); ver, sub, cnt = struct.unpack_from('<iii', doo, 4); assert len(doo) == 16 + cnt*50 + 8
for name in ('war3map.w3u', 'war3map.w3t'):
    u = a.read(name); q = 8; norig = struct.unpack_from('<i', u, 4)[0]
    def table(q, count):
        for _ in range(count):
            q += 8; m = struct.unpack_from('<i', u, q)[0]; q += 4
            for _ in range(m):
                q += 4; t = struct.unpack_from('<i', u, q)[0]; q += 4
                q = u.index(b'\0', q) + 1 if t == 3 else q + 4
                assert u[q:q+4] == b'\0\0\0\0'; q += 4
        return q
    q = table(8, norig); ncust = struct.unpack_from('<i', u, q)[0]; q = table(q + 4, ncust)
    assert q == len(u); print(name, 'ok', norig, 'edited,', ncust, 'custom')
print('w3e ok', ground, w, h, '| wpm', pw, ph, '| doo', cnt)
S = 6
img = Image.new('RGB', (pw * S // 4, ph * S // 4)); px = img.load()
col = {0x40: (90, 75, 60), 0x4A: (15, 8, 25), 0xCE: (0, 0, 0)}
for cy in range(0, ph, 4):
    for cx in range(0, pw, 4):
        c = col.get(wpm[16 + cy*pw + cx], (255, 0, 0))
        for yy in range(S):
            for xx in range(S):
                px[cx // 4 * S + xx, (ph - 1 - cy) // 4 * S + yy - S + 1 if False else (ph // 4 - 1 - cy // 4) * S + yy] = c
d = ImageDraw.Draw(img)
def P(x, y): return ((x + LY.HALF) / 128 * S, (LY.HALF - y) / 128 * S)
for k in range(cnt):
    o = 16 + k*50; tid = doo[o:o+4].decode(); x, y = struct.unpack_from('<ff', doo, o+8); cx, cy = P(x, y)
    if tid.startswith('ITw'):
        if tid == 'ITw0': d.rectangle([cx-10*S/8, cy-S/4, cx+10*S/8, cy+S/4], fill=(150, 170, 200))
        else: d.rectangle([cx-S/4, cy-10*S/8, cx+S/4, cy+10*S/8], fill=(150, 170, 200))
    else:
        d.ellipse([cx-2, cy-2, cx+2, cy+2], fill=(255, 200, 40))
for L in range(8):
    d.line([P(*pt) for pt in LY.lane_waypoints(L)], fill=(255, 60, 60), width=1)
    cx, cy = P(*LY.hero_spot(L)); d.text((cx-3, cy-6), str(L+1), fill=(255, 255, 255))
for L in range(8):
    cx, cy = P(*LY.nexus_pos(L)); d.rectangle([cx-10, cy-10, cx+10, cy+10], outline=(255, 0, 255), width=2)
    cx, cy = P(*LY.tower_pos(L)); d.rectangle([cx-4, cy-4, cx+4, cy+4], fill=(255, 0, 255))
for (dx, dy) in LY.HALL_TAVERNS:
    cx, cy = P(*LY.hall_point(dx, dy)); d.rectangle([cx-9, cy-9, cx+9, cy+9], outline=(0, 255, 120), width=2)
for (k, x, y) in LY.GROVE_BUILDINGS:
    cx, cy = P(x, y); d.rectangle([cx-9, cy-9, cx+9, cy+9], outline=(0, 200, 255), width=2)
cx, cy = P(0, 0); d.rectangle([cx-12, cy-12, cx+12, cy+12], outline=(80, 80, 255), width=3)
img.save(out_png); print('preview ->', out_png)
