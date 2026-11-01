#!/usr/bin/env python3
"""Real-engine balance measurements: production game, ordinary orders, hidden runs (docs/balance.md).

    tools/balance_probe.py run LABEL [--set fight|progress|stall|smoke] [--workers 2]
    tools/balance_probe.py report LABEL
    tools/balance_probe.py selfcheck     the log validation, on fixtures, no game

Each scenario is a map built with `build.py --probe` (the production script + gen/probe.j) and played by
tools/test_env.py in its own Wine prefix, on a hidden display. Fixed champion, purchases, seed and orders, so the
same scenario can be repeated before and after a change. A lost fight is data. Results stay under
~/games/wc3-test-env/evidence/balance-LABEL/, one folder per run plus results.jsonl.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("CD_TEST_ROOT", Path.home() / "games" / "wc3-test-env"))

HEROES = {"dryad": (0, "S"), "mk": (1, "A"), "archmage": (4, "D"), "beastmaster": (8, "A")}      # index in the tavern, primary stat shop key: ranged, melee, caster, summoner
# 1000 gold: every build is legal at the start and costs what the shop asks.
BUILDS = {
    "naked": lambda primary: "",
    "starter": lambda primary: "FFFFAASSP",                             # 4 x All, 2 x Str, 2 x Agi, potion: 941 g at +5 % per buy
    "primary": lambda primary: primary * 7 + "P",                       # 7 x the primary stat, potion: 914 g (8 x would cost 1056 g since v4.4)
    "careless": lambda primary: "WWWWEEEE",                             # 4 x Mana, 4 x Damage, no potion (the log records the gold spent)
    "duel1": lambda primary: "V",                                       # Vampire Fang rank 1, then the cycle below with what is left
    "duel5": lambda primary: "VVVVV",                                   # Vampire Fang rank 5, then the cycle
}
CYCLES = {"starter": "FFAS", "primary": None, "duel1": "FFAS", "duel5": "FFAS"}


def fight_set():
    """The first waves on the money of the start: no purchase after the first 5 s."""
    runs = []
    for hero in HEROES:
        for build in BUILDS:
            for seed in ((1, 2) if build in ("naked", "starter") else (1,)):
                runs.append({"name": f"{hero}-{build}-s{seed}", "hero": hero, "build": build, "seed": seed, "mode": 0, "duration": 180, "timeout": 500})
    return runs


def progress_set():
    """Mid and late waves reached by playing: every coin goes to the build's cycle, every tree to the Bank."""
    return [{"name": f"{hero}-progress-s1", "hero": hero, "build": "starter", "seed": 1, "mode": 1, "duration": 420, "timeout": 800} for hero in HEROES]


def stall_set():
    """From wave 3, walk away from the last monsters and stay away, while the Bank pays and the gold stays unspent."""
    return [{"name": "dryad-stall-s1", "hero": "dryad", "build": "starter", "seed": 1, "mode": 2, "stall_wave": 3, "duration": 420, "timeout": 800}]


def boss_set():
    """A lane boss at wave 10 and 20, after playing there with every coin spent. The tower and Nexus are killed once for it: the bot does not push."""
    return [{"name": f"{hero}-boss-w{wave}", "hero": hero, "build": "starter", "seed": 1, "mode": 3, "stall_wave": wave, "duration": 900, "timeout": 1300}
            for hero in ("dryad", "mk", "archmage", "beastmaster") for wave in (10, 20)]


def duel_set():
    """One boss, one champion, a legal loadout bought in the real shops: Fang rank 1 early, rank 5 late, the rest of the gold in the FFAS cycle.
    Level, wave and gold are a fixture, not a natural playthrough. It ends at the first death or 120 s after first contact."""
    runs = []
    for hero in ("mk", "dryad"):
        runs.append({"name": f"{hero}-warden-w10", "hero": hero, "build": "duel1", "seed": 1, "mode": 4, "stall_wave": 10, "duel_level": 10, "duel_budget": 5000, "duel_nexus": False, "duration": 300, "timeout": 600})
        runs.append({"name": f"{hero}-nexusboss-w20", "hero": hero, "build": "duel5", "seed": 1, "mode": 4, "stall_wave": 20, "duel_level": 20, "duel_budget": 20000, "duel_nexus": True, "duration": 300, "timeout": 600})
    return runs


def smoke_set():
    return [{"name": "dryad-smoke", "hero": "dryad", "build": "starter", "seed": 1, "mode": 0, "duration": 80, "timeout": 300}]


SETS = {"fight": fight_set, "progress": progress_set, "stall": stall_set, "boss": boss_set, "duel": duel_set, "smoke": smoke_set}


def build_map(run, out_dir):
    index, primary = HEROES[run["hero"]]
    cycle = CYCLES.get(run["build"], "")
    if run["mode"] not in (1, 3, 4):
        cycle = ""            # fight: no purchase after the start; stall: gold stays unspent, so the log shows the Bank directly
    elif cycle is None:
        cycle = primary
    config = {"hero": index, "mode": run["mode"], "seed": run["seed"], "buy": BUILDS[run["build"]](primary), "cycle": cycle,
              "duration": run["duration"], "stall_wave": run.get("stall_wave", 3), "duel_level": run.get("duel_level", 1),
              "duel_budget": run.get("duel_budget", 1000), "duel_nexus": run.get("duel_nexus", False)}
    game = ROOT / "slots" / "a" / "prefix" / "drive_c" / "war3"
    env = dict(os.environ, CD_PROBE=json.dumps(config), WC3_DIR=str(game if game.is_dir() else ""))
    done = subprocess.run([sys.executable, "build.py", "--probe"], cwd=REPO, env=env, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"build failed for {run['name']}:\n{done.stdout[-1500:]}\n{done.stderr[-1500:]}")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{run['name']}.w3x"
    shutil.copy2(REPO / "dist" / "TechToolsCastleDefence_PROBE.w3x", target)
    return target, config


WAVE_PARTS = {"wave": ("why", "spawned_at", "spawned", "first_hit", "first_deal", "hp_min", "deaths_wave"),
              "incoming": ("taken", "from_wave", "from_tower", "from_nexus", "from_boss", "from_other", "hits"),
              "dealt": ("hero_wave_raw", "hero_wave_hp", "hero_other_raw", "hero_other_hp", "other_raw", "other_hp"),
              "state": ("level", "xp", "kills", "deaths", "castle", "gold", "spent", "earned", "income", "trees", "alive", "casts"),
              "team": ("playing", "heroes")}
PRELOAD_LIMIT = 259     # the engine cuts a Preload line there


def parse_results(path):
    """The log of one run. A line at the engine's limit or a wave record with a missing part or field is an error."""
    data = path.read_bytes().decode("utf-8", "replace") if path.exists() else ""
    lines = re.findall(r'Preload\( "(.*?)" \)', data)
    errors = [f"line at the Preload limit: {line[:60]}..." for line in lines if len(line) >= PRELOAD_LIMIT - 4]
    events = [dict(re.findall(r"(\w+)=(\S*)", line)) for line in lines if line.startswith("M t=")]
    waves = {}
    for event in events:
        kind = event.get("event")
        if kind in WAVE_PARTS and "wave" in event:
            waves.setdefault(event["wave"], {}).setdefault(kind, event)
    records = []
    for number_text, parts in sorted(waves.items(), key=lambda kv: int(kv[0])):
        record = {"wave": number_text, "t": parts.get("wave", {}).get("t"), "pending": parts.get("state", {}).get("pending")}
        for kind, fields in WAVE_PARTS.items():
            for field in fields:
                if field not in parts.get(kind, {}):
                    errors.append(f"wave {number_text}: {kind}.{field} missing")
                else:
                    record[field] = parts[kind][field]
        records.append(record)
    return {"lines": lines, "events": events, "records": records, "errors": errors, "fail": [line for line in lines if line.startswith("FAIL")], "done": any("SELFTEST DONE" in line for line in lines)}


def summarize(run, parsed):
    events = parsed["events"]
    first = {}
    for event in events:
        first.setdefault(event.get("event"), event)
    last = next((e for e in reversed(events) if e.get("event") == "final"), {})
    end = next((e for e in reversed(events) if e.get("event") == "end"), {})
    return {"name": run["name"], "hero": run["hero"], "build": run["build"], "seed": run["seed"], "mode": run["mode"],
            "start": first.get("start"), "ready": first.get("ready"), "waves": parsed["records"], "errors": parsed["errors"],
            "casts": [e for e in events if e.get("event") == "cast"], "ranks": next((e for e in reversed(events) if e.get("event") == "ranks"), {}),
            "channels_cancelled": [e for e in events if e.get("event") == "channel_cancelled"],
            "channels": [e for e in events if e.get("event") == "channel"], "summons": [e for e in events if e.get("event") == "summon"],
            "other_damage": [e for e in events if e.get("event") == "other_damage"],
            "duel_start": next((e for e in events if e.get("event") == "duel_start"), {}), "duel_end": next((e for e in events if e.get("event") == "duel_end"), {}),
            "duel_damage": next((e for e in events if e.get("event") == "duel_damage"), {}), "boss_casts": [e for e in events if e.get("event") == "boss_cast"],
            "boss_channels": [e for e in events if e.get("event") == "boss_channel"], "buys_fang": [e for e in events if e.get("event") == "buy_ok" and e.get("item") == "fang"],
            "duel_loadout": next((e for e in events if e.get("event") == "duel_loadout"), {}),
            "levels": [e for e in events if e.get("event") == "level"], "deaths": [e for e in events if e.get("event") == "death"],
            "tower_hits": [e for e in events if e.get("event") == "tower_hit"], "progress": [e for e in events if e.get("event") in ("tower_destroyed", "nexus_destroyed", "boss_slain", "castle_destroyed")],
            "pending_at_end": [e for e in events if e.get("event") == "buy_pending_at_end"],
            "buys_ok": [e for e in events if e.get("event") == "buy_ok"], "buys_failed": [e for e in events if e.get("event") in ("buy_failed", "buy_refused")],
            "stall": [e for e in events if e.get("event") == "stall_start"], "beats": [e for e in events if e.get("event") == "beat"], "final": last, "end": end, "fail": parsed["fail"], "done": parsed["done"]}


def run_one(run, slot, label, base, lock):
    run_id = f"balance-{label}-{run['name']}"
    evidence = ROOT / "evidence" / run_id
    cmd = [sys.executable, str(REPO / "tools" / "test_env.py"), "run", "--slot", slot, "--map", str(run["map"]), "--timeout", str(run["timeout"]),
           "--stall", "300", "--start-timeout", "120", "--shot-every", "30", "--run-id", run_id]
    started = time.time()
    with open(base / f"{run['name']}.out", "wb") as out:
        code = subprocess.run(cmd, stdout=out, stderr=out, check=False).returncode
    parsed = parse_results(evidence / "cd_test.txt")
    row = summarize(run, parsed)
    try:
        result = json.loads((evidence / "result.json").read_text())
    except (OSError, ValueError):
        result = {}
    row.update(runner_exit=code, verdict=result.get("verdict"), war3=result.get("war3"), map_sha256=result.get("map_sha256"),
               evidence=str(evidence), seconds=round(time.time() - started), config=run["config"], personal_zero=(result.get("personal_diff") or {}).get("zero"))
    with lock:
        with open(base / "results.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"[{time.strftime('%H:%M:%S')}] {run['name']} on {slot}: exit {code} {row['verdict']}, waves {len(row['waves'])}, deaths {len(row['deaths'])}", flush=True)


def cmd_run(args):
    base = ROOT / "evidence" / f"balance-{args.label}"
    base.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True, check=False).stdout.splitlines()
    runs = SETS[args.set]()
    if args.only:
        runs = [r for r in runs if re.search(args.only, r["name"])]
    for run in runs:           # dist/ is shared: every map is built here, one at a time, before any game starts
        run["map"], run["config"] = build_map(run, base / "maps")
        run["map_sha256"] = hashlib.sha256(Path(run["map"]).read_bytes()).hexdigest()
    with open(base / "meta.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "set": args.set, "git_head": head, "git_dirty": dirty,
                            "maps": {r["name"]: r["map_sha256"] for r in runs}}) + "\n")
    queue = list(runs)
    lock = threading.Lock()

    def worker(slot):
        while True:
            with lock:
                if not queue:
                    return
                run = queue.pop(0)
            run_one(run, slot, args.label, base, lock)
    threads = [threading.Thread(target=worker, args=(slot,)) for slot in args.slots[:args.workers]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"results: {base / 'results.jsonl'}")
    return 0


NUMERIC = [field for fields in WAVE_PARTS.values() for field in fields if field not in ("why", "playing", "heroes")]


def finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_row(row):
    """Why this run cannot be used. Empty = a complete log, whatever the fight's result: a lost fight is a valid measurement."""
    problems = list(row.get("errors") or []) + list(row.get("fail") or [])
    if row.get("runner_exit") != 0 or row.get("verdict") != "PASS":
        problems.append(f"runner: exit {row.get('runner_exit')} verdict {row.get('verdict')}")
    if not row.get("done"):
        problems.append("no SELFTEST DONE")
    if row.get("mode") == 4:
        # a duel has no wave records: its own end record, a loadout really bought, the champion's kit used
        if not row.get("duel_end", {}).get("winner") or not row.get("duel_damage"):
            problems.append("no duel_end record")
        wanted = (row.get("config") or {}).get("buy", "").count("V")
        if len(row.get("buys_fang", [])) != wanted or str(row.get("duel_loadout", {}).get("fang_rank")) != str(wanted):
            problems.append(f"Fang: wanted rank {wanted}, {len(row.get('buys_fang', []))} buys, carried rank {row.get('duel_loadout', {}).get('fang_rank')}")
        if any(int(b["gold_before"]) - int(b["gold_after"]) != 1000 for b in row.get("buys_fang", [])):
            problems.append("a Fang buy did not cost 1000 gold")
        if row.get("hero") == "dryad":
            if str(row.get("ranks", {}).get("r1", "0")) in ("0", ""):
                problems.append("the Dryad never learned Multiple Arrows")
        elif not row.get("casts"):
            problems.append(f"{row.get('hero')}: not one spell cast")
        return problems
    # a champion who only swung his weapon says nothing about his spells; the Dryad's kit is passive, but her Multiple Arrows must be learned
    if row.get("hero") == "dryad":
        if str(row.get("ranks", {}).get("r1", "0")) in ("0", ""):
            problems.append("the Dryad never learned Multiple Arrows")
    elif not row.get("casts"):
        problems.append(f"{row.get('hero')}: not one spell cast")
    for name in ("start", "ready", "final", "end"):
        if not row.get(name):
            problems.append(f"no {name} record")
    start = row.get("start") or {}
    if start and start.get("heroes") != "0,":
        problems.append(f"not a solo champion at the start: {start.get('heroes')}")
    if not row.get("end", {}).get("why"):
        problems.append("end without a reason")
    numbers = [int(w["wave"]) for w in row.get("waves", []) if str(w.get("wave", "")).isdigit()]
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append(f"wave records are not 1..N: {numbers[:12]}")
    last = row.get("end", {}).get("wave")
    if last is not None and str(last).isdigit() and int(last) != len(numbers):
        problems.append(f"the run ended in wave {last}, but {len(numbers)} wave records")
    if not numbers:
        problems.append("no wave record")
    for wave in row.get("waves", []):
        for field in NUMERIC:
            if not finite(wave.get(field)):
                problems.append(f"wave {wave.get('wave')}: {field}={wave.get(field)!r} is not a number")
        if wave.get("heroes") != "0,":
            problems.append(f"wave {wave.get('wave')}: heroes={wave.get('heroes')!r}")
    for name, fields in (("ready", ("maxhp", "gold", "spent")), ("final", ("maxhp", "gold", "spent", "earned", "level"))):
        for field in fields:
            if row.get(name) and not finite(row[name].get(field)):
                problems.append(f"{name}.{field}={row[name].get(field)!r} is not a number")
    return problems


def report_rows(label):
    path = ROOT / "evidence" / f"balance-{label}" / "results.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    good = []
    for row in rows:
        problems = validate_row(row)
        if problems:
            print(f"INVALID {row['name']}: {problems[:3]}", file=sys.stderr)
        else:
            good.append(row)
    return good


def cmd_report(args):
    rows = report_rows(args.label)
    rows.sort(key=lambda r: (r["hero"], r["build"], r["seed"]))
    code = lambda text: int(text).to_bytes(4, "big").decode("latin1")
    print("| run | learned (card order) | spell casts by id | channels: id, seconds | summoned: type x n | damage: champion / other player units, by type | channels cancelled |")
    print("|---|---|---|---|---|---|---|")
    for row in rows:
        counts = {}
        for cast in row.get("casts", []):
            counts[code(cast["id"])] = counts.get(code(cast["id"]), 0) + 1
        summoned = {}
        for summon in row.get("summons", []):
            summoned[code(summon["type"])] = summoned.get(code(summon["type"]), 0) + 1
        ranks = " ".join(row.get("ranks", {}).get(f"r{i}", "?") for i in range(5))
        hero_damage = sum(float(w["hero_wave_raw"]) + float(w["hero_other_raw"]) for w in row["waves"])
        other_damage = sum(float(w["other_raw"]) for w in row["waves"])
        spells = ", ".join(f"{name} {n}" for name, n in sorted(counts.items()))
        channels = ", ".join(f"{code(c['id'])} {c['seconds']}" for c in row.get("channels", []))
        kinds = ", ".join(f"{name} x{n}" for name, n in sorted(summoned.items()))
        others = ", ".join(f"{code(o['type'])} {o['raw']}" for o in row.get("other_damage", []))
        print(f"| {row['name']} | {ranks} | {spells} | {channels} | {kinds} | {hero_damage:.0f} / {other_damage:.0f} ({others}) | {len(row.get('channels_cancelled', []))} |")
    print()
    duels = [r for r in rows if r.get("mode") == 4]
    rows = [r for r in rows if r.get("mode") != 4]
    if duels:
        print("| duel | boss HP | winner | seconds | hero HP left / max | lowest | boss HP left | damage: hero / his others / from boss | casts | boss casts by id | boss channels: id, seconds, finished |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for row in duels:
            end, dmg = row["duel_end"], row["duel_damage"]
            spells = {}
            for cast in row.get("boss_casts", []):
                spells[code(cast["id"])] = spells.get(code(cast["id"]), 0) + 1
            channels = ", ".join(f"{code(c['id'])} {c['seconds']} {c['finished']}" for c in row.get("boss_channels", []))
            print(f"| {row['name']} | {row['duel_start'].get('hp')} | {end.get('winner')} | {end.get('fight_s')} | {end.get('hero_hp')} / {end.get('hero_max')} | {dmg.get('hp_min')} | {end.get('boss_hp')} | {dmg.get('hero_raw')} / {dmg.get('others_raw')} / {dmg.get('from_boss')} | {dmg.get('casts')} | {spells} | {channels} |")
        print()
    print("A row with a tower hit is a separate class (tower): never evidence of how strong the monsters are.\n")
    print("| run | class | ready HP | wave | spawned | fight s | first hit s | taken wave/tower | HP min | deaths | level | gold spent+earned | castle |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        for wave in row["waves"][:args.waves]:
            at = float(wave["spawned_at"])
            first = float(wave["first_hit"])
            kind = "tower" if float(wave["from_tower"]) > 0 else "monsters"
            print(f"| {row['name']} | {kind} | {row['ready']['maxhp']} | {wave['wave']} | {wave['spawned']} | {float(wave['t']) - at:.0f}{' (open)' if wave['why'] == 'open_at_end' else ''} | "
                  f"{first - at if first >= 0 else float('nan'):.1f} | {wave['from_wave']}/{wave['from_tower']} | {wave['hp_min']} | {wave['deaths_wave']} | {wave['level']} | {wave['spent']}+{wave['earned']} | {wave['castle']} |")
    return 0


def fixture_log(waves=2, drop=(), replace=None):
    """A short log in the probe's format, for the checks of validate_row without a game."""
    out = ["M config mode=0", "M t=0.0 event=start hero=Dryad playing=0,8,9,10,11, heroes=0,", "M t=5.0 event=ready hero=Dryad maxhp=2550 gold=76 spent=924 earned=0"]
    for w in range(1, waves + 1):
        out += [f"M t={30 + w}.0 event=wave wave={w} why=cleared spawned_at=30.0 spawned=7 first_hit=34.1 first_deal=31.9 hp_min=2496 deaths_wave=0",
                f"M t={30 + w}.0 event=incoming wave={w} taken=78 from_wave=78 from_tower=0 from_nexus=0 from_boss=0 from_other=0 hits=7",
                f"M t={30 + w}.0 event=dealt wave={w} hero_wave_raw=1801 hero_wave_hp=1314 hero_other_raw=0 hero_other_hp=0 other_raw=9 other_hp=9",
                f"M t={30 + w}.0 event=state wave={w} level=2 xp=200 kills=7 deaths=0 castle=8000 gold=83 spent=924 earned=7 income=0 trees=1 alive=0 casts=0",
                f"M t={30 + w}.0 event=team wave={w} playing=0,8,9,10,11, heroes=0,"]
    out += [f"M t=80.0 event=final hero=Dryad level=2 maxhp=2575 gold=83 spent=924 earned=7", "M t=80.0 event=ranks r0=0 r1=2 r2=0 r3=0 r4=0", f"M t=80.0 event=end why=limit tower_hits=0 nexus_hits=0 wave={waves} deaths=0", "PASS probe finished: limit", "SELFTEST DONE"]
    out = [line for line in out if not any(d in line for d in drop)]
    if replace:
        out = [line.replace(*replace) for line in out]
    return "\n".join(f'call Preload( "{line}" )' for line in out)


def economy_settled(row):
    """Is the last spent/earned of a run exact? True or False from the log; None = unknown: logs from before the pending
    field cannot say (their last figures can be off by one purchase)."""
    if row.get("pending_at_end"):
        return False
    last = row["waves"][-1].get("pending") if row.get("waves") else None
    if last is None:
        return None
    return last == "0"


def fixture_row(text, **extra):
    path = Path(tempfile.mkstemp(suffix=".txt")[1])
    path.write_text(text)
    row = summarize({"name": "fixture", "hero": "dryad", "build": "starter", "seed": 1, "mode": 0}, parse_results(path))
    path.unlink()
    row.update(runner_exit=0, verdict="PASS")
    row.update(extra)
    return row


def cmd_selfcheck(_args):
    """validate_row against a good log and against every way a log can be incomplete, without a game."""
    cases = [("complete log", fixture_row(fixture_log()), True),
             ("a lost fight is still valid", fixture_row(fixture_log(replace=("deaths_wave=0", "deaths_wave=3"))), True),
             ("castle destroyed is still valid", fixture_row(fixture_log(replace=("why=limit", "why=castle_destroyed"))), True),
             ("no SELFTEST DONE", fixture_row(fixture_log(drop=("SELFTEST DONE",))), False),
             ("no ready record", fixture_row(fixture_log(drop=("event=ready",))), False),
             ("no final record", fixture_row(fixture_log(drop=("event=final",))), False),
             ("no end record", fixture_row(fixture_log(drop=("event=end",))), False),
             ("no start record", fixture_row(fixture_log(drop=("event=start",))), False),
             ("a whole wave missing", fixture_row(fixture_log(waves=3, drop=("wave=2 ",))), False),
             ("wave part missing", fixture_row(fixture_log(drop=("event=state wave=2",))), False),
             ("cut field", fixture_row(fixture_log(replace=("castle=8000", "cast"))), False),
             ("empty number", fixture_row(fixture_log(replace=("taken=78", "taken="))), False),
             ("not a number", fixture_row(fixture_log(replace=("hp_min=2496", "hp_min=abc"))), False),
             ("infinite number", fixture_row(fixture_log(replace=("hp_min=2496", "hp_min=inf"))), False),
             ("a second champion", fixture_row(fixture_log(replace=("heroes=0,", "heroes=0,1,"))), False),
             ("a line at the engine's limit", fixture_row(fixture_log(replace=("event=final", "event=final pad=" + "x" * 260))), False),
             ("FAIL line", fixture_row(fixture_log() + '\ncall Preload( "FAIL probe: wrong hero" )'), False),
             ("runner exit not 0", fixture_row(fixture_log(), runner_exit=3), False),
             ("runner verdict not PASS", fixture_row(fixture_log(), verdict="TIMEOUT"), False),
             ("a Dryad without her spears", fixture_row(fixture_log(replace=("r1=2", "r1=0"))), False),
             ("casts field missing", fixture_row(fixture_log(replace=(" casts=0", ""))), False),
             ("a caster without one spell", dict(fixture_row(fixture_log()), hero="mk"), False),
             ("a caster with a spell", dict(fixture_row(fixture_log()), hero="mk", casts=[{"event": "cast", "id": "1"}]), True)]
    bad = 0
    pending = fixture_row(fixture_log() + '\ncall Preload( "M t=80.0 event=buy_pending_at_end item=F price=103 gold_before=900 gold=797" )')
    settled = fixture_row(fixture_log(replace=("income=0", "pending=0 income=0")))
    raw = fixture_row(fixture_log(replace=("income=0", "pending=1 income=0")))
    for name, ok in (("a purchase unsettled at the end is reported", pending["pending_at_end"] and economy_settled(pending) is False),
                     ("pending=0 in the log: settled", economy_settled(settled) is True),
                     ("pending=1 in the log: not settled", economy_settled(raw) is False),
                     ("no pending field (an old log): unknown, not settled", economy_settled(fixture_row(fixture_log())) is None)):
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    for name, row, wanted in cases:
        problems = validate_row(row)
        ok = (not problems) == wanted
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {problems[:1]}")
    print(f"selfcheck: {len(cases) + 4 - bad} of {len(cases) + 4}")
    return 1 if bad else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("label")
    run.add_argument("--set", default="fight", choices=sorted(SETS))
    run.add_argument("--only", help="regular expression on the scenario names")
    run.add_argument("--workers", type=int, default=2)
    run.add_argument("--slots", default="ab", help="one letter per slot")
    report = sub.add_parser("report")
    report.add_argument("label")
    report.add_argument("--waves", type=int, default=3)
    sub.add_parser("selfcheck")
    args = parser.parse_args()
    return {"run": cmd_run, "report": cmd_report, "selfcheck": cmd_selfcheck}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
