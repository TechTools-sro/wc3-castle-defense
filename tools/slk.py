"""Tiny SYLK (.slk) + profile (.txt) readers for WC3 game data."""
import re

def read_slk(path):
    rows = {}; cur_y = None
    for line in open(path, 'rb').read().decode('latin1').splitlines():
        if not line.startswith('C;'):
            continue
        fields = {}
        for part in line.split(';')[1:]:
            if part:
                fields[part[0]] = part[1:]
        if 'Y' in fields:
            cur_y = int(fields['Y'])
        x = int(fields['X'])
        v = fields.get('K', '')
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        rows.setdefault(cur_y, {})[x] = v
    head = rows.pop(1)
    out = {}
    for y, cols in rows.items():
        rec = {head[x]: v for x, v in cols.items() if x in head}
        key = rec.get(head[1])
        if key:
            out[key] = rec
    return out

def read_profile(path):
    out = {}; cur = None
    for line in open(path, 'rb').read().decode('latin1').splitlines():
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            cur = out.setdefault(line[1:-1], {})
        elif '=' in line and cur is not None and not line.startswith('//'):
            k, v = line.split('=', 1)
            cur[k] = v
    return out
