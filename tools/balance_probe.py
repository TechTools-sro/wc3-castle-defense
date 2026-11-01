#!/usr/bin/env python3
"""Real-engine balance measurements: production game, ordinary orders, hidden runs (docs/balance.md).

    tools/balance_probe.py run LABEL [--set fight|progress|stall|smoke] [--workers 2]
    tools/balance_probe.py report LABEL

Each scenario is a map built with `build.py --probe` (the production script + gen/probe.j) and played by
tools/test_env.py in its own Wine prefix, on a hidden display. Fixed champion, purchases, seed and orders, so the
same scenario can be repeated before and after a change. A lost fight is data. Results stay under
~/games/wc3-test-env/evidence/balance-LABEL/, one folder per run plus results.jsonl.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("CD_TEST_ROOT", Path.home() / "games" / "wc3-test-env"))

HEROES = {"dryad": (0, "S"), "mk": (1, "A"), "archmage": (4, "D")}      # index in the tavern, primary stat shop key
# 1000 gold: every build is legal at the start and costs what the shop asks.
BUILDS = {
    "naked": lambda primary: "",
    "starter": lambda primary: "FFFFAASSP",                             # 4 x All, 2 x Str, 2 x Agi, potion: 924 g
    "primary": lambda primary: primary * 8 + "P",                       # 8 x the primary stat, potion: 989 g
    "careless": lambda primary: "WWWWEEEE",                             # 4 x Mana, 4 x Damage: 856 g, no potion
}
CYCLES = {"starter": "FFAS", "primary": None}


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
    """Leave the last monster alive from wave 3 and let the Bank pay."""
    return [{"name": "dryad-stall-s1", "hero": "dryad", "build": "starter", "seed": 1, "mode": 2, "stall_wave": 3, "duration": 420, "timeout": 800}]


def smoke_set():
    return [{"name": "dryad-smoke", "hero": "dryad", "build": "starter", "seed": 1, "mode": 0, "duration": 80, "timeout": 300}]


SETS = {"fight": fight_set, "progress": progress_set, "stall": stall_set, "smoke": smoke_set}


def build_map(run, out_dir):
    index, primary = HEROES[run["hero"]]
    cycle = CYCLES.get(run["build"], "")
    if run["mode"] == 0:
        cycle = ""
    elif cycle is None:
        cycle = primary
    config = {"hero": index, "mode": run["mode"], "seed": run["seed"], "buy": BUILDS[run["build"]](primary), "cycle": cycle,
              "duration": run["duration"], "stall_wave": run.get("stall_wave", 3)}
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
              "state": ("level", "xp", "kills", "deaths", "castle", "gold", "spent", "earned", "income", "trees", "alive"),
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
        record = {"wave": number_text, "t": parts.get("wave", {}).get("t")}
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
            "levels": [e for e in events if e.get("event") == "level"], "deaths": [e for e in events if e.get("event") == "death"],
            "tower_hits": [e for e in events if e.get("event") == "tower_hit"], "progress": [e for e in events if e.get("event") in ("tower_destroyed", "nexus_destroyed", "boss_slain", "castle_destroyed")],
            "buys_ok": [e for e in events if e.get("event") == "buy_ok"], "buys_failed": [e for e in events if e.get("event") in ("buy_failed", "buy_refused")],
            "beats": [e for e in events if e.get("event") == "beat"], "final": last, "end": end, "fail": parsed["fail"], "done": parsed["done"]}


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
    threads = [threading.Thread(target=worker, args=(slot,)) for slot in "ab"[:args.workers]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"results: {base / 'results.jsonl'}")
    return 0


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# why = cleared, or next_wave_before_clear: also a finished wave (the next one proves it), the observer just missed the
# moment between two 0.25 s ticks; its `alive` then counts the new wave. open_at_end = the run ended during this wave.
# from_other is a residual: it can hold a late missile of a monster already removed from gWaveUnits. `taken` is exact.
def report_rows(label):
    path = ROOT / "evidence" / f"balance-{label}" / "results.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    bad = [(r["name"], r["errors"][:2], r["fail"][:1]) for r in rows if r["errors"] or r["fail"] or r["runner_exit"] != 0]
    if bad:
        print(f"INVALID RUNS, do not use: {bad}", file=sys.stderr)
    return [r for r in rows if not (r["errors"] or r["fail"] or r["runner_exit"] != 0)]


def cmd_report(args):
    rows = report_rows(args.label)
    rows.sort(key=lambda r: (r["hero"], r["build"], r["seed"]))
    print("| run | ready HP | wave | spawned | fight s | first hit s | taken wave/tower | HP min | deaths | level | gold earned | castle |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        ready = row.get("ready") or {}
        for wave in row["waves"][:args.waves]:
            at = number(wave.get("spawned_at"))
            print(f"| {row['name']} | {ready.get('maxhp', '')} | {wave.get('wave')} | {wave.get('spawned')} | {number(wave.get('t')) - at:.0f}{' (open)' if wave.get('why') == 'open_at_end' else ''} | "
                  f"{number(wave.get('first_hit')) - at:.1f} | {wave.get('from_wave')}/{wave.get('from_tower')} | {wave.get('hp_min')} | {wave.get('deaths_wave')} | {wave.get('level')} | {wave.get('earned')} | {wave.get('castle')} |")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("label")
    run.add_argument("--set", default="fight", choices=sorted(SETS))
    run.add_argument("--only", help="regular expression on the scenario names")
    run.add_argument("--workers", type=int, default=2)
    report = sub.add_parser("report")
    report.add_argument("label")
    report.add_argument("--waves", type=int, default=3)
    args = parser.parse_args()
    return {"run": cmd_run, "report": cmd_report}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
