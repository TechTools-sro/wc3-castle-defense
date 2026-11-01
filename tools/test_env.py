#!/usr/bin/env python3
"""Hidden, isolated WarCraft III self-test of the map, safe while the owner plays.

    tools/test_env.py run                build the TEST map, run it hidden, exit 0 only on a fresh clean SELFTEST DONE
    tools/test_env.py concurrency        two hidden clients at once + the owner's client if it runs (evidence for isolation)
    tools/test_env.py verify-branches    error paths: refusals, timeout, game killed, runner killed
    tools/test_env.py cleanup [--slot a] [--force]  stop whatever is left of a slot (only that slot)
    tools/test_env.py status             what runs, per slot, and the owner's client (read-only)

Everything lives under ~/games/wc3-test-env (CD_TEST_ROOT): slots/<slot>/ = own Wine prefix with its own copy of the
game (no hardlinks, no symlinks to the original), own HOME and runtime dir; evidence/<run-id>/ = what a run proved.
The game draws on a private Xvfb with a private cookie, in software (lavapipe), audio driver off. Nothing is shown on
the owner's desktop, and no click or focus change is ever sent. Details: docs/test-env.md.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import select
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
import traceback
import types
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("CD_TEST_ROOT", HOME / "games" / "wc3-test-env"))
REAL_GAME = Path(os.environ.get("WC3_DIR", HOME / "games" / "warcraft3"))
PERSONAL_PREFIXES = [HOME / ".wine"] + ([Path(os.environ["WINEPREFIX"])] if os.environ.get("WINEPREFIX") else [])

WINE = "/usr/bin/wine"
WINESERVER = "/usr/lib/x86_64-linux-gnu/wine/wineserver"   # not in PATH on this machine
LAVAPIPE = "/usr/share/vulkan/icd.d/lvp_icd.json"          # software Vulkan: Xvfb has no GPU path, and the GPU is his
TEST_MAP = "TechToolsCastleDefence_TEST.w3x"
MAP_WIN = "Maps\\Test\\" + TEST_MAP
WIDTH, HEIGHT = 800, 600

# Only what the game needs. An allow-list, so saves, replays, maps, profiles and anything added later stay out.
GAME_FILES = ["war3.exe", "game.dll", "Storm.dll", "Mss32.dll", "ijl15.dll", "blizzard.ax", "d3d8.dll", "d3d9.dll",
              "msvcr120.dll", "msvcp120.dll", "war3.mpq", "War3x.mpq", "War3xlocal.mpq", "War3Patch.mpq",
              "BlizzardError.exe", "Warcraft III.exe", "Frozen Throne.exe"]
GAME_DIRS = ["Redist"]
MUTABLE = ["CustomMapData", "Maps", "replay", "save", "TempReplay.w3g"]   # wiped before every run

# The whole registry seed. Nothing is copied from the owner's prefix.
REG_SEED = r"""REGEDIT4

[HKEY_CURRENT_USER\Software\Wine\Drivers]
"Audio"=""

[HKEY_CURRENT_USER\Software\Wine\DllOverrides]
"winemenubuilder.exe"=""
"mscoree"=""
"mshtml"=""
"d3d8"="native"
"d3d9"="native"

[HKEY_CURRENT_USER\Software\Wine\WineDbg]
"ShowCrashDialog"=dword:00000000

[HKEY_CURRENT_USER\Software\Blizzard Entertainment\Warcraft III\Misc]
"seenintromovie"=dword:00000001

[HKEY_CURRENT_USER\Software\Blizzard Entertainment\Warcraft III\Sound]
"ambient"=dword:00000000
"environmental"=dword:00000000
"movement"=dword:00000000
"music"=dword:00000000
"nosoundwarn"=dword:00000001
"positional"=dword:00000000
"sfx"=dword:00000000
"unit"=dword:00000000

[HKEY_CURRENT_USER\Software\Blizzard Entertainment\Warcraft III\Video]
"animquality"=dword:00000000
"colordepth"=dword:00000020
"lights"=dword:00000000
"maxfps"=dword:0000001e
"modeldetail"=dword:00000000
"occlusion"=dword:00000000
"particles"=dword:00000000
"resheight"=dword:00000258
"reswidth"=dword:00000320
"spellfilter"=dword:00000000
"texquality"=dword:00000000
"unitshadows"=dword:00000000

[HKEY_CURRENT_USER\Software\Blizzard Entertainment\Warcraft III\Gameplay]
"autosaveReplay"=dword:00000000
"netgameport"=dword:00001837
"""

EXIT_OK, EXIT_FAILED_CHECKS, EXIT_REFUSED, EXIT_TIMEOUT, EXIT_NO_RESULT, EXIT_CRASH, EXIT_ISOLATION = 0, 1, 2, 3, 4, 5, 6
EXIT_INTERRUPTED = 130


class Refused(Exception):
    """A safety check said no. Nothing was started."""


class Interrupted(Exception):
    pass


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, default=str)
        f.write("\n")
    os.replace(tmp, path)


def append_jsonl(path, data):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")


def pause(seconds):
    time.sleep(seconds)


# ---------------------------------------------------------------------------------------------------------------------
# Path safety: nothing destructive runs on a path that was not proven to be ours.

def no_symlink_chain(path):
    p = Path(path)
    for part in [p, *p.parents]:
        try:
            if stat.S_ISLNK(os.lstat(part).st_mode):
                return str(part)
        except FileNotFoundError:
            continue
    return None


def is_within(child, parent):
    child, parent = os.path.abspath(child), os.path.abspath(parent)
    return child == parent or child.startswith(parent.rstrip("/") + "/")


def validate_root():
    if not ROOT.is_absolute():
        raise Refused(f"CD_TEST_ROOT must be absolute: {ROOT}")
    link = no_symlink_chain(ROOT)
    if link:
        raise Refused(f"test root path contains a symlink ({link}) - refusing")
    if ROOT.exists() and os.lstat(ROOT).st_uid != os.getuid():
        raise Refused(f"test root is not owned by this user: {ROOT}")
    for personal in PERSONAL_PREFIXES + [REAL_GAME, HOME, Path("/")]:
        if is_within(ROOT, personal) and personal not in (HOME, Path("/")):
            raise Refused(f"test root {ROOT} is inside {personal} - refusing")
        if is_within(personal, ROOT):
            raise Refused(f"test root {ROOT} contains {personal} - refusing")
        if ROOT.exists() and personal.exists() and os.path.samefile(ROOT, personal):
            raise Refused(f"test root {ROOT} is the same directory as {personal} - refusing")


class Slot:
    def __init__(self, name):
        if not re.fullmatch(r"[a-z0-9]{1,8}", name):
            raise Refused(f"bad slot name: {name}")
        self.name = name
        self.dir = ROOT / "slots" / name
        self.prefix = self.dir / "prefix"
        self.game = self.prefix / "drive_c" / "war3"
        self.home = self.dir / "home"
        self.runtime = self.dir / "runtime"
        self.tmp = self.dir / "tmp"
        self.run_dir = self.dir / "run"
        self.xauth = self.run_dir / "xauth"
        self.state = self.run_dir / "state.json"
        self.results = self.game / "CustomMapData" / "TestResults" / "cd_test.txt"

    def assert_own(self, path):
        if not is_within(path, self.dir):
            raise Refused(f"{path} is not inside {self.dir}")
        link = no_symlink_chain(path)
        if link:
            raise Refused(f"{path} goes through a symlink ({link}) - refusing")

    def assert_prefix(self):
        self.assert_own(self.prefix)
        if not self.prefix.is_dir():
            raise Refused(f"prefix is not a real directory: {self.prefix}")
        for personal in PERSONAL_PREFIXES:
            if personal.exists() and os.path.samefile(self.prefix, personal):
                raise Refused(f"prefix {self.prefix} is the personal prefix {personal} - refusing")
        c_drive = self.prefix / "dosdevices" / "c:"
        if c_drive.exists() and not is_within(os.path.realpath(c_drive), self.prefix):
            raise Refused(f"{c_drive} leaves the prefix")

    def env(self, run_id="setup", display=None):
        """The complete environment of everything started in this slot: nothing is inherited."""
        env = {
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "USER": os.environ.get("USER", "novakj"),
            "LOGNAME": os.environ.get("LOGNAME", os.environ.get("USER", "novakj")),
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_DATA_HOME": str(self.home / ".local/share"), "XDG_CACHE_HOME": str(self.home / ".cache"),
            "XDG_RUNTIME_DIR": str(self.runtime), "TMPDIR": str(self.tmp),
            "WINEPREFIX": str(self.prefix), "WINEARCH": "win64", "WINEDEBUG": "-all",
            "WINEDLLOVERRIDES": "winemenubuilder.exe=d;mscoree=d;mshtml=d;d3d8=n;d3d9=n",
            "VK_DRIVER_FILES": LAVAPIPE, "VK_ICD_FILENAMES": LAVAPIPE, "LP_NUM_THREADS": "2",
            "LIBGL_ALWAYS_SOFTWARE": "1", "__GLX_VENDOR_LIBRARY_NAME": "mesa", "DXVK_STATE_CACHE": "0", "DXVK_LOG_LEVEL": "info",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent", "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent",
            "PULSE_SERVER": "unix:/nonexistent", "PIPEWIRE_REMOTE": "/nonexistent",
            "CD_TEST_SLOT": str(self.dir), "CD_TEST_RUN": run_id,
        }
        if display is not None:
            env["DISPLAY"] = f":{display}"
            env["XAUTHORITY"] = str(self.xauth)
        return env

    def wineserver(self, *args, timeout=30):
        self.assert_prefix()
        env = self.env(display=read_state(self).get("display"))
        return subprocess.run([WINESERVER, *args], env=env, cwd=self.dir, timeout=timeout,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)


# ---------------------------------------------------------------------------------------------------------------------
# Processes: identity = PID + start time + the exact environment marker, never a name pattern.

def proc_info(pid):
    with open(f"/proc/{pid}/stat", "rb") as f:
        raw = f.read()
    end = raw.rindex(b")")
    comm = raw[raw.index(b"(") + 1:end].decode(errors="replace")
    fields = raw[end + 2:].split()
    return {"pid": pid, "comm": comm, "state": fields[0].decode(), "ppid": int(fields[1]), "cpu_ticks": int(fields[11]) + int(fields[12]),
            "starttime": int(fields[19]), "rss_kb": int(fields[21]) * (os.sysconf("SC_PAGE_SIZE") // 1024)}


def proc_environ(pid):
    with open(f"/proc/{pid}/environ", "rb") as f:
        return f.read().split(b"\0")


def all_pids():
    return [int(name) for name in os.listdir("/proc") if name.isdigit()]


def own_processes(slot):
    """Live processes of this slot. A process is ours only if its environment carries this slot's exact markers."""
    marks = (f"CD_TEST_SLOT={slot.dir}".encode(), f"WINEPREFIX={slot.prefix}".encode())
    found = []
    for pid in all_pids():
        if pid == os.getpid():
            continue
        try:
            env = proc_environ(pid)
            if not (marks[0] in env or marks[1] in env):
                continue
            info = proc_info(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if info["state"] != "Z":
            found.append(info)
    return found


def signal_verified(slot, pid, starttime, sig):
    """Re-check the identity through a pidfd, so a recycled PID can never be hit."""
    marks = (f"CD_TEST_SLOT={slot.dir}".encode(), f"WINEPREFIX={slot.prefix}".encode())
    try:
        fd = os.pidfd_open(pid)
    except (ProcessLookupError, OSError):
        return False
    try:
        env = proc_environ(pid)
        if proc_info(pid)["starttime"] != starttime or not (marks[0] in env or marks[1] in env):
            return False
        signal.pidfd_send_signal(fd, sig)
        return True
    except (ProcessLookupError, FileNotFoundError, PermissionError):
        return False
    finally:
        os.close(fd)


def wait_gone(slot, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if not own_processes(slot):
            return True
        pause(0.2)
    return not own_processes(slot)


def cleanup_slot(slot, reason):
    """Stop everything of this slot and nothing else, in the order prefix server, then verified leftovers."""
    report = {"slot": slot.name, "reason": reason, "started": now(), "before": own_processes(slot), "signalled": []}
    if report["before"]:
        try:
            if any(p["comm"] == "wineserver" for p in report["before"]):
                done = slot.wineserver("-k", timeout=20)
                report["wineserver_k"] = {"rc": done.returncode, "out": done.stdout[-400:]}
        except (subprocess.TimeoutExpired, Refused) as e:
            report["wineserver_k"] = {"error": str(e)}
        wait_gone(slot, 8)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            left = own_processes(slot)
            if not left:
                break
            for p in left:
                if signal_verified(slot, p["pid"], p["starttime"], sig):
                    report["signalled"].append({"sig": sig.name, "pid": p["pid"], "starttime": p["starttime"], "comm": p["comm"]})
            wait_gone(slot, 5)
    # Xvfb killed hard leaves its lock and socket behind: remove only the display this slot recorded.
    state = read_state(slot)
    display = state.get("display")
    if display and not own_processes(slot):
        lock, sock = Path(f"/tmp/.X{display}-lock"), Path(f"/tmp/.X11-unix/X{display}")
        try:
            holder = int(lock.read_text().strip())
        except (OSError, ValueError):
            holder = None
        if holder is not None and holder == state.get("xvfb_pid") and not Path(f"/proc/{holder}").exists():
            for leftover in (lock, sock):
                try:
                    leftover.unlink()
                    report.setdefault("removed", []).append(str(leftover))
                except OSError:
                    pass
    report["after"] = own_processes(slot)
    report["ended"] = now()
    report["clean"] = not report["after"]
    if report["clean"] and slot.state.exists():
        slot.assert_own(slot.state)
        slot.state.unlink()
    return report


def read_state(slot):
    try:
        return json.loads(slot.state.read_text())
    except (OSError, ValueError):
        return {}


def foreign_clients():
    """Wine processes that are not ours, a game (war3*) or a wineserver: read-only, /proc only."""
    found = []
    slots_dir = str(ROOT / "slots") + "/"
    for pid in all_pids():
        try:
            info = proc_info(pid)
            if not (info["comm"].lower().startswith("war3") or info["comm"] == "wineserver") or info["state"] == "Z":
                continue
            env = dict(item.split(b"=", 1) for item in proc_environ(pid) if b"=" in item)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        prefix = env.get(b"WINEPREFIX", str(HOME / ".wine").encode()).decode(errors="replace")
        if prefix.startswith(slots_dir):
            continue
        found.append({"pid": pid, "starttime": info["starttime"], "comm": info["comm"], "prefix": prefix,
                      "display": env.get(b"DISPLAY", b"").decode(errors="replace")})
    return found


def same_process(identity):
    try:
        info = proc_info(identity["pid"])
    except (FileNotFoundError, ProcessLookupError):
        return False
    return info["starttime"] == identity["starttime"] and info["state"] != "Z"


# ---------------------------------------------------------------------------------------------------------------------
# Slot setup.

def copy_game(slot, log):
    """Real copies only. Unchanged files are kept, so a later run does not copy 800 MB again."""
    if not (REAL_GAME / "war3.exe").is_file():
        raise Refused(f"no game at {REAL_GAME}")
    wanted = [REAL_GAME / name for name in GAME_FILES]
    for name in GAME_DIRS:
        wanted += [p for p in sorted((REAL_GAME / name).rglob("*")) if p.is_file()]
    if shutil.disk_usage(ROOT).free < 3 << 30:
        raise Refused(f"less than 3 GiB free under {ROOT}")
    copied = 0
    for src in wanted:
        if src.is_symlink():
            raise Refused(f"unexpected symlink in the game: {src}")
        dest = slot.game / src.relative_to(REAL_GAME)
        slot.assert_own(dest)
        st = src.stat()
        if dest.is_file():
            d = dest.stat()
            if d.st_size == st.st_size and int(d.st_mtime) == int(st.st_mtime):
                continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".copy")
        shutil.copy2(src, tmp)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dest)
        copied += 1
    log(f"game copy: {len(wanted)} files, {copied} copied")
    return wanted


def assert_game_independent(slot, wanted):
    """Mutable game files must never share an inode with the original."""
    problems = []
    for src in wanted:
        dest = slot.game / src.relative_to(REAL_GAME)
        s, d = src.stat(), os.lstat(dest)
        if stat.S_ISLNK(d.st_mode) or d.st_nlink != 1 or (s.st_dev, s.st_ino) == (d.st_dev, d.st_ino):
            problems.append(str(dest))
    if problems:
        raise Refused(f"game copy shares files with the original: {problems[:5]}")


def prefix_audit(slot):
    audit = {"dosdevices": {}, "links": {}, "bad": []}
    dosdevices = slot.prefix / "dosdevices"
    for entry in sorted(os.listdir(dosdevices)):
        target = os.readlink(dosdevices / entry)
        audit["dosdevices"][entry] = target
        if entry == "c:" or re.fullmatch(r"com\d+", entry):
            continue
        audit["bad"].append(f"drive {entry} -> {target}")
    users = slot.prefix / "drive_c" / "users"
    for user_dir in sorted(users.iterdir()):
        for entry in sorted(user_dir.iterdir()):
            if entry.is_symlink():
                real = os.path.realpath(entry)
                audit["links"][str(entry.relative_to(users))] = real
                if not is_within(real, slot.dir):
                    audit["bad"].append(f"{entry} -> {real}")
    return audit


def start_xvfb(slot, env, log_path):
    """-displayfd lets the server pick a free number itself. The cookie matches any display number."""
    slot.run_dir.mkdir(parents=True, exist_ok=True)
    name, cookie = b"MIT-MAGIC-COOKIE-1", secrets.token_bytes(16)
    field = lambda b: struct.pack(">H", len(b)) + b
    fd = os.open(slot.xauth, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(struct.pack(">H", 0xFFFF) + field(b"") + field(b"") + field(name) + field(cookie))
    read_end, write_end = os.pipe()
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(["/usr/bin/Xvfb", "-displayfd", str(write_end), "-screen", "0", f"{WIDTH}x{HEIGHT}x24",
                                 "-nolisten", "tcp", "-auth", str(slot.xauth), "-noreset"],
                                env=env, cwd=slot.dir, stdout=log, stderr=log, pass_fds=(write_end,), start_new_session=True)
    os.close(write_end)
    ready, _, _ = select.select([read_end], [], [], 20)
    number = os.read(read_end, 32).decode().strip() if ready else ""
    os.close(read_end)
    if not number.isdigit():
        proc.terminate()
        raise Refused(f"Xvfb did not report a display: see {log_path}")
    number = int(number)
    host = os.environ.get("DISPLAY", ":0").lstrip(":").split(".")[0]
    if number == 0 or str(number) == host:
        proc.terminate()
        raise Refused(f"Xvfb picked the owner's display :{number}")
    return proc, number


def stop_xvfb(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def ensure_slot(name, log, evidence):
    slot = Slot(name)
    for path in (slot.dir, slot.prefix, slot.game, slot.home, slot.runtime, slot.tmp, slot.run_dir):
        slot.assert_own(path)
    for path in (slot.dir, slot.home, slot.runtime, slot.tmp, slot.run_dir):
        path.mkdir(parents=True, exist_ok=True)
    os.chmod(slot.dir, 0o700)
    os.chmod(slot.runtime, 0o700)
    ready_file = slot.dir / "prefix.ready"
    version = subprocess.run([WINE, "--version"], capture_output=True, text=True, check=False, env=slot.env()).stdout.strip()
    seed_hash = hashlib.sha256(REG_SEED.encode()).hexdigest()
    ready = ready_file.read_text().split() if ready_file.exists() else []
    if ready != [version.replace(" ", "_"), seed_hash]:
        log(f"preparing Wine prefix of slot {name} ({version})")
        setup_prefix(slot, log, evidence)
        ready_file.write_text(f"{version.replace(' ', '_')} {seed_hash}\n")
    slot.assert_prefix()
    wanted = copy_game(slot, log)
    assert_game_independent(slot, wanted)
    audit = prefix_audit(slot)
    if audit["bad"]:
        raise Refused(f"prefix audit failed: {audit['bad']}")
    return slot, audit


def setup_prefix(slot, log, evidence):
    env_no_display = slot.env()
    xvfb, display = start_xvfb(slot, env_no_display, evidence / "setup-xvfb.log")
    env = slot.env(display=display)
    write_state(slot, {"purpose": "setup", "display": display, "xvfb_pid": xvfb.pid})
    try:
        with open(evidence / "setup-wine.log", "ab") as out:
            def wine(*args, timeout=240):
                subprocess.run([WINE, *args], env=env, cwd=slot.home, stdout=out, stderr=out, timeout=timeout, check=True)
            if not (slot.prefix / "system.reg").exists():
                wine("wineboot", "--init")
                slot.wineserver("-w", timeout=120)
            # A drive that maps / would let the game reach the owner's files.
            z_drive = slot.prefix / "dosdevices" / "z:"
            if z_drive.is_symlink():
                z_drive.unlink()
            seed = slot.prefix / "drive_c" / "cd_seed.reg"
            seed.write_text(REG_SEED, encoding="latin-1")
            wine("regedit", "/S", "C:\\cd_seed.reg", timeout=60)
            seed.unlink()
            slot.wineserver("-w", timeout=60)
    finally:
        cleanup_report = cleanup_slot(slot, "setup finished")
        stop_xvfb(xvfb)
        write_json(evidence / "setup-cleanup.json", cleanup_report)
    user_reg = (slot.prefix / "user.reg").read_text(encoding="latin-1")
    if '[Software\\\\Wine\\\\Drivers]' not in user_reg or '"Audio"=""' not in user_reg:
        raise Refused("the audio driver setting did not reach the prefix registry")
    log("prefix ready")


def write_state(slot, data):
    slot.run_dir.mkdir(parents=True, exist_ok=True)
    write_json(slot.state, data)


def wipe_mutable(slot):
    for name in MUTABLE:
        path = slot.game / name
        slot.assert_own(path)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    slot.results.parent.mkdir(parents=True, exist_ok=True)
    (slot.game / "Maps" / "Test").mkdir(parents=True, exist_ok=True)


def install_map(slot, map_path):
    """Atomic, into this slot's copy only."""
    dest = slot.game / "Maps" / "Test" / TEST_MAP
    slot.assert_own(dest)
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.copy2(map_path, tmp)
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    return sha256(dest)


def build_test_map(game_dir, log, evidence):
    """The build reads game data from a private copy and never installs. dist/ is shared, so one build at a time,
    and the caller keeps its own copy of the result under the same lock (snapshot_map)."""
    env = dict(os.environ, WC3_DIR=str(game_dir))
    with open(evidence / "build.log", "wb") as out:
        done = subprocess.run([sys.executable, "build.py", "--test", "--no-install"], cwd=REPO, env=env, stdout=out, stderr=out, check=False)
    if done.returncode != 0:
        raise Refused(f"build failed, see {evidence / 'build.log'}")
    log("built the TEST map")
    return REPO / "dist" / TEST_MAP


def snapshot_map(game_dir, map_arg, log, evidence):
    """A read-only copy of the map that belongs to this run. Nothing later can change what it tests."""
    fd = os.open(ROOT / "build.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        source = Path(map_arg) if map_arg else build_test_map(game_dir, log, evidence)
        if not source.is_file():
            raise Refused(f"no such map: {source}")
        target = evidence / TEST_MAP
        shutil.copy2(source, target)
        os.chmod(target, 0o444)
    finally:
        os.close(fd)
    return target


# ---------------------------------------------------------------------------------------------------------------------
# What a run proves.

def read_results(path):
    try:
        data = path.read_bytes().decode("utf-8", "replace")
    except OSError:
        return []
    return re.findall(r'Preload\( "(.*?)" \)', data)


def evaluate_results(lines):
    passes = [line for line in lines if line.startswith("PASS")]
    fails = [line for line in lines if line.startswith("FAIL")]
    return {"lines": len(lines), "pass": len(passes), "fail": len(fails), "done": any("SELFTEST DONE" in line for line in lines), "failed": fails}


def final_gate(prior, lines, results_mtime, game_started, new_crash):
    """The only way to exit 0: the monitor saw the end, and the file read AFTER the game stopped is fresh,
    complete and clean, with no new crash evidence. Returns (verdict, reason, exit code)."""
    verdict, reason, code = prior
    state = evaluate_results(lines)
    if new_crash:
        return "CRASH", f"new crash evidence: {sorted(new_crash)[:3]}", EXIT_CRASH
    if code != EXIT_OK:
        return prior
    if results_mtime is None or game_started is None:
        return "NO_RESULT", "no results file", EXIT_NO_RESULT
    if results_mtime < game_started:
        return "STALE_RESULT", "the results file is older than this game", EXIT_NO_RESULT
    if not state["done"]:
        return "NO_RESULT", "no SELFTEST DONE line in the final results", EXIT_NO_RESULT
    if state["fail"]:
        return "FAILED_CHECKS", f"{state['fail']} FAIL lines", EXIT_FAILED_CHECKS
    if not state["pass"]:
        return "NO_RESULT", "no PASS line in the final results", EXIT_NO_RESULT
    return verdict, reason, code


def war3_environment(pid):
    """What the game really inherited: proof that nothing of the owner's session reached it."""
    keep = re.compile(r"^(WINE\w*|DISPLAY|XAUTHORITY|WAYLAND_DISPLAY|DBUS_\w+|PULSE_SERVER|PIPEWIRE_REMOTE|HOME|XDG_RUNTIME_DIR|VK_\w+|CD_TEST_\w+)=")
    return sorted(item.decode(errors="replace") for item in proc_environ(pid) if keep.match(item.decode(errors="replace")))


def crash_fingerprint(slot):
    """Every file and folder in the slot's crash places, with size, mtime and hash, so that a new entry in an old
    log counts as much as a new crash folder."""
    roots = [slot.game / "Errors"]
    users = slot.prefix / "drive_c" / "users"
    if users.is_dir():
        roots += [user_dir / "AppData" / "Local" / "Temp" / "BlizzardError" for user_dir in users.iterdir()]
    found = {}
    for root in roots:
        for base, dirs, files in os.walk(root):
            for name in dirs:
                found[os.path.join(base, name) + "/"] = "folder"
            for name in files:
                path = os.path.join(base, name)
                try:
                    st = os.stat(path)
                    found[path] = [st.st_size, st.st_mtime_ns, sha256(path)]
                except OSError:
                    found[path] = "unreadable"
    return found


def crash_changes(before, after):
    return {path for path, mark in after.items() if before.get(path) != mark}


def personal_snapshot():
    """Size + mtime of the real game tree, hashes of the owner's registry, and the places a fresh Wine could touch."""
    snap = {"game": {}, "wine": {}, "home": {}}
    for base, _, files in os.walk(REAL_GAME):
        for name in files:
            path = os.path.join(base, name)
            try:
                st = os.lstat(path)
            except OSError:
                continue
            snap["game"][os.path.relpath(path, REAL_GAME)] = [st.st_size, st.st_mtime_ns]
    for name in ("system.reg", "user.reg", "userdef.reg"):
        path = HOME / ".wine" / name
        if path.exists():
            snap["wine"][name] = sha256(path)
    crash_dir = HOME / ".wine" / "drive_c" / "users" / os.environ.get("USER", "novakj") / "AppData" / "Local" / "Temp" / "BlizzardError"
    snap["wine"]["crash_folders"] = sorted(os.listdir(crash_dir)) if crash_dir.is_dir() else []
    for rel in (".local/share/applications", ".config/menus/applications-merged", ".local/share/mime/packages", ".local/share/desktop-directories", "Desktop", "Documents"):
        path = HOME / rel
        snap["home"][rel] = sorted(os.listdir(path)) if path.is_dir() else None
    return snap


def snapshot_diff(before, after):
    diff = {}
    for section in before:
        for key in sorted(set(before[section]) | set(after[section])):
            if before[section].get(key, "<none>") != after[section].get(key, "<none>"):
                diff[f"{section}:{key}"] = [before[section].get(key, "<none>"), after[section].get(key, "<none>")]
    return diff


def process_audit(slot, pid):
    """What the game really holds open and maps. A path of the real game or the owner's prefix is a violation."""
    forbidden = [str(REAL_GAME) + "/", str(HOME / ".wine") + "/"]
    devices = ("/dev/snd", "/dev/nvidia", "/dev/dri")
    audit = {"pid": pid, "violations": [], "devices": [], "paths_in_slot": 0, "other_paths": set(), "socket_inodes": set()}
    targets = []
    try:
        for fd in os.listdir(f"/proc/{pid}/fd"):
            try:
                targets.append(os.readlink(f"/proc/{pid}/fd/{fd}"))
            except OSError:
                pass
        with open(f"/proc/{pid}/maps", encoding="utf-8", errors="replace") as f:
            targets += [line.split(None, 5)[5].strip() for line in f if len(line.split(None, 5)) == 6]
    except OSError as e:
        audit["error"] = str(e)
    for target in targets:
        if target.startswith("socket:["):
            audit["socket_inodes"].add(target[8:-1])
        elif target.startswith(devices):
            audit["devices"].append(target)
            audit["violations"].append(target)
        elif any(target.startswith(p) for p in forbidden):
            audit["violations"].append(target)
        elif target.startswith(str(slot.dir) + "/"):
            audit["paths_in_slot"] += 1
        elif target.startswith("/") and not target.startswith(("/usr/", "/dev/null", "/dev/zero", "/dev/urandom", "/proc/", "/sys/", "/memfd", "/SYSV", "/dev/pts", "/dev/ptmx")):
            audit["other_paths"].add(target)
    audit["other_paths"] = sorted(audit["other_paths"])
    # An accepted Pulse/PipeWire socket has the server path as local address and the client's inode as peer.
    peers = subprocess.run(["ss", "-xpn"], capture_output=True, text=True, check=False).stdout.splitlines()
    audit["audio_socket_peers"] = [line.split()[:8] for line in peers if ("pulse" in line or "pipewire" in line) and any(f" {i} " in f" {line} " for i in audit["socket_inodes"])]
    if audit["audio_socket_peers"]:
        audit["violations"].append("audio server socket")
    audit["socket_inodes"] = len(audit["socket_inodes"])
    return audit


def host_windows():
    """Windows on the owner's display that could be ours. Read-only X query, no input and no focus."""
    try:
        out = subprocess.run(["xwininfo", "-root", "-tree", "-display", os.environ.get("DISPLAY", ":0")], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"available": False, "error": str(e)}
    if out.returncode != 0:
        return {"available": False, "error": out.stderr[:200]}
    lines = out.stdout.splitlines()
    return {"available": True, "total": len(lines), "wine": [line.strip()[:120] for line in lines if re.search(r"cdiso|Wine desktop|war3\.exe|Warcraft", line)]}


def start_video(env, display, path, seconds):
    """A short film of the hidden display, asked for by the map itself: a 'VIDEO name seconds' line in its results."""
    return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "x11grab", "-framerate", "25", "-video_size", f"{WIDTH}x{HEIGHT}", "-i", f":{display}",
                             "-t", str(seconds), "-c:v", "libx264", "-preset", "ultrafast", "-qp", "10", str(path)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def hover_shot(env, display, path, x, y):
    """The map asks to look at a button: 'HOVER name x y' in its results. The pointer of this private display goes there, and only there; no click."""
    path.parent.mkdir(parents=True, exist_ok=True)
    moved = subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    time.sleep(1.3)
    done = screenshot(env, display, path)
    subprocess.run(["xdotool", "mousemove", "400", "250"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    return moved.returncode == 0 and done


def screenshot(env, display, path):
    try:
        done = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "x11grab", "-video_size", f"{WIDTH}x{HEIGHT}", "-i", f":{display}", "-frames:v", "1", str(path)],
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=False)
    except subprocess.TimeoutExpired:
        return False
    return done.returncode == 0 and path.exists()


# ---------------------------------------------------------------------------------------------------------------------
# One hidden run.

def acquire_slot(wanted):
    (ROOT / "slots").mkdir(parents=True, exist_ok=True)
    names = [wanted] if wanted != "auto" else ["a", "b"]
    end = time.time() + 20     # a watchdog that just finished cleaning may still hold the lock for a moment
    while True:
        for name in names:
            slot = Slot(name)
            slot.assert_own(slot.dir)
            slot.dir.mkdir(parents=True, exist_ok=True)
            fd = os.open(slot.dir / "lock", os.O_RDWR | os.O_CREAT, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return name, fd
            except OSError:
                os.close(fd)
        if time.time() >= end:
            raise Refused(f"slot {wanted} is busy (tools/test_env.py status)")
        pause(1)


def start_watchdog(slot, evidence):
    """Survives a killed runner (kill -9, a closed terminal) and cleans the slot. It keeps the slot lock while it does."""
    read_end, write_end = os.pipe()
    pid = os.fork()
    if pid:
        os.close(read_end)
        return write_end
    try:
        os.close(write_end)
        os.setsid()
        for sig in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM):
            signal.signal(sig, signal.SIG_IGN)
        devnull = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(devnull, fd)
        word = os.read(read_end, 16)
        if word != b"done":
            report = cleanup_slot(slot, "runner died: watchdog")
            write_json(evidence / "cleanup-watchdog.json", report)
    finally:
        os._exit(0)


def cpu_share(slot_name, count):
    cpus = sorted(os.sched_getaffinity(0))
    index = "ab".find(slot_name)
    index = max(index, 0)
    chosen = cpus[-count * (index + 1):len(cpus) - count * index]
    return chosen if len(chosen) == count else cpus


def run_once(args):
    validate_root()
    slot_name, lock_fd = acquire_slot(args.slot)
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-{slot_name}-{secrets.token_hex(2)}"
    evidence = ROOT / "evidence" / run_id
    evidence.mkdir(parents=True, exist_ok=False)
    os.chmod(ROOT, 0o700)

    def log(message):
        line = f"[{time.strftime('%H:%M:%S')} {slot_name}] {message}"
        print(line, flush=True)
        with open(evidence / "run.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def on_signal(signum, _frame):
        raise Interrupted(signal.Signals(signum).name)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, on_signal)

    # Everything started from here inherits low priority and a few CPUs, so the owner's game keeps the machine.
    os.sched_setaffinity(0, cpu_share(slot_name, args.cpus))
    os.nice(10)
    subprocess.run(["ionice", "-c3", "-p", str(os.getpid())], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    slot = Slot(slot_name)
    watchdog = start_watchdog(slot, evidence)
    meta = {"run_id": run_id, "slot": slot_name, "slot_dir": str(slot.dir), "evidence": str(evidence), "started": now(), "timeout_s": args.timeout,
            "git_head": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip(),
            "git_dirty": subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True, check=False).stdout.splitlines(),
            "cpus": sorted(os.sched_getaffinity(0))}
    write_json(evidence / "run.json", meta)
    result = {"run_id": run_id, "slot": slot_name, "verdict": "UNFINISHED", "reason": "", "exit_code": EXIT_INTERRUPTED}
    xvfb = None
    personal_before = None
    foreign_start = []
    gate = {"crash_before": None, "game_started": None}
    try:
        stale = cleanup_slot(slot, "before run: leftovers of an earlier run")
        write_json(evidence / "cleanup-before.json", stale)
        if not stale["clean"]:
            raise Refused(f"could not clean slot {slot_name}: {stale['after']}")
        slot, audit = ensure_slot(slot_name, log, evidence)
        write_json(evidence / "prefix-audit.json", audit)
        wipe_mutable(slot)
        map_path = snapshot_map(slot.game, args.map, log, evidence)
        result["map_sha256"] = sha256(map_path)
        if install_map(slot, map_path) != result["map_sha256"]:
            raise Refused("the map in the slot differs from the run's copy")
        result["map_source"] = args.map or "built by this run"
        crash_before = crash_fingerprint(slot)
        gate["crash_before"] = crash_before

        personal_before = personal_snapshot()
        foreign_start = foreign_clients()
        windows_before = host_windows()
        write_json(evidence / "foreign-before.json", {"clients": foreign_start, "host_windows": windows_before, "at": now()})
        if foreign_start:
            log(f"other Wine processes run, read-only from here: {foreign_start}")

        xvfb, display = start_xvfb(slot, slot.env(run_id), evidence / "xvfb.log")
        write_state(slot, {"run_id": run_id, "display": display, "xvfb_pid": xvfb.pid, "xvfb_starttime": proc_info(xvfb.pid)["starttime"], "runner_pid": os.getpid()})
        env = slot.env(run_id, display)
        x_info = subprocess.run(["xdpyinfo", "-display", f":{display}"], env=env, capture_output=True, text=True, check=False)
        (evidence / "xdpyinfo.txt").write_text(x_info.stdout + x_info.stderr)
        result["display"] = display
        result["xvfb"] = {"pid": xvfb.pid, "starttime": proc_info(xvfb.pid)["starttime"]}

        screens = evidence / "screens"
        screens.mkdir()
        wine_log = open(evidence / "wine.log", "ab")
        started = time.time()
        gate["game_started"] = started
        # -loadfile before -window: never the argument order of the old visible runner.
        game_cmd = [WINE, "explorer", f"/desktop=cdiso-{slot_name},{WIDTH}x{HEIGHT}", "C:\\war3\\war3.exe", "-loadfile", MAP_WIN, "-window"]
        subprocess.Popen(game_cmd, env=env, cwd=slot.game, stdout=wine_log, stderr=wine_log, start_new_session=True)
        log(f"game started on private display :{display}, evidence {evidence}")

        status = run_monitor(slot, args, evidence, env, display, started, result, log, foreign_start, crash_before)
        result.update(status)
        wine_log.close()
    except Interrupted as e:
        result.update(verdict="INTERRUPTED", reason=f"signal {e}", exit_code=EXIT_INTERRUPTED)
        log(f"interrupted by {e}")
    except Refused as e:
        result.update(verdict="REFUSED", reason=str(e), exit_code=EXIT_REFUSED)
        log(f"REFUSED: {e}")
    except Exception as e:        # a bug in the runner still cleans up, and never reads as a pass
        result.update(verdict="RUNNER_ERROR", reason=repr(e), exit_code=EXIT_REFUSED)
        log(f"RUNNER_ERROR: {e!r}\n{traceback.format_exc()}")
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        finish_run(slot, evidence, result, xvfb, personal_before, foreign_start, log, gate)
        os.write(watchdog, b"done")
        os.close(watchdog)
        os.close(lock_fd)
    return result["exit_code"]


def run_monitor(slot, args, evidence, env, display, started, result, log, foreign_start, crash_before):
    deadline = started + args.timeout
    war3 = None
    last_lines = -1
    last_change = started
    last_shot = 0.0
    shot_count = 0
    audited = False
    outcome = None
    foreign_last = foreign_start
    videos = {}
    hovers = set()
    while outcome is None:
        pause(1.0)
        elapsed = time.time() - started
        own = own_processes(slot)
        current = next((p for p in own if p["comm"].lower().startswith("war3")), None)
        if current and not war3:
            war3 = {"pid": current["pid"], "starttime": current["starttime"], "comm": current["comm"]}
            result["war3"] = dict(war3, wineprefix=str(slot.prefix), display=f":{display}")
            server = next((p for p in own if p["comm"] == "wineserver"), None)
            if server:
                result["wineserver"] = {"pid": server["pid"], "starttime": server["starttime"], "server_dir": os.readlink(f"/proc/{server['pid']}/cwd")}
            log(f"war3.exe PID {war3['pid']} starttime {war3['starttime']}, wineserver {result.get('wineserver')}")
            write_json(evidence / "war3-env.json", war3_environment(war3["pid"]))
        lines = read_results(slot.results)
        state = evaluate_results(lines)
        for line in lines:
            parts = line.split()
            if len(parts) == 3 and parts[0] == "VIDEO" and parts[1] not in videos and re.fullmatch(r"[a-z0-9-]+", parts[1]) and parts[2].isdigit():
                videos[parts[1]] = start_video(env, display, evidence / f"video-{parts[1]}.mp4", min(int(parts[2]), 60))
                log(f"filming {parts[1]} for {parts[2]} s")
            if len(parts) == 4 and parts[0] == "HOVER" and parts[1] not in hovers and re.fullmatch(r"[A-Za-z0-9-]+", parts[1]) and parts[2].isdigit() and parts[3].isdigit():
                hovers.add(parts[1])
                if not hover_shot(env, display, evidence / "hover" / f"{parts[1]}.png", int(parts[2]), int(parts[3])):
                    log(f"hover {parts[1]}: no picture")
        if state["lines"] != last_lines:
            last_lines, last_change = state["lines"], time.time()
            append_jsonl(evidence / "progress.jsonl", {"at": now(), "elapsed_s": round(elapsed, 1), "pass": state["pass"], "fail": state["fail"], "lines": state["lines"],
                                                       "last": lines[-1] if lines else "", "war3_alive": bool(current),
                                                       "cpu_ticks": current["cpu_ticks"] if current else None, "rss_kb": current["rss_kb"] if current else None})
            log(f"{elapsed:5.0f} s  PASS {state['pass']}  FAIL {state['fail']}  {(lines[-1] if lines else '')[:70]}")
            if lines and current and not audited:
                audit = process_audit(slot, current["pid"])
                write_json(evidence / "process-audit.json", audit)
                audited = True
                if audit["violations"]:
                    return {"verdict": "ISOLATION_VIOLATION", "reason": f"{audit['violations'][:5]}", "exit_code": EXIT_ISOLATION, **state}
        if time.time() - last_shot >= args.shot_every:
            last_shot = time.time()
            shot_count += 1
            shot = evidence / "screens" / f"s{shot_count:03d}-{int(elapsed):04d}s.png"
            if screenshot(env, display, shot):
                append_jsonl(evidence / "screens.jsonl", {"file": shot.name, "elapsed_s": round(elapsed, 1), "sha1": hashlib.sha1(shot.read_bytes()).hexdigest()})
        write_json(evidence / "status.json", {"at": now(), "elapsed_s": round(elapsed, 1), "pass": state["pass"], "fail": state["fail"], "done": state["done"],
                                               "war3": result.get("war3"), "wineserver": result.get("wineserver"), "display": display,
                                               "cpu_ticks": current["cpu_ticks"] if current else None, "rss_kb": current["rss_kb"] if current else None,
                                               "shots": shot_count})
        foreign_now = foreign_clients()
        if foreign_now != foreign_last:
            foreign_last = foreign_now
            append_jsonl(evidence / "foreign.jsonl", {"at": now(), "clients": foreign_now})
        new_crash = crash_changes(crash_before, crash_fingerprint(slot))
        holding = state["done"] and args.hold_file and not Path(args.hold_file).exists()
        if new_crash:
            outcome = dict(state, verdict="CRASH", reason=f"new crash evidence: {sorted(new_crash)[:3]}", exit_code=EXIT_CRASH)
        elif state["done"] and not holding:
            pause(2.0)
            screenshot(env, display, evidence / "screens" / "final.png")
            if current:
                audit = process_audit(slot, current["pid"])
                write_json(evidence / "process-audit-final.json", audit)
                if audit["violations"]:
                    return dict(state, verdict="ISOLATION_VIOLATION", reason=f"{audit['violations'][:5]}", exit_code=EXIT_ISOLATION)
            outcome = dict(state, verdict="PASS", reason="", exit_code=EXIT_OK)   # final_gate still has the last word
        elif war3 and not same_process(war3):
            outcome = dict(state, verdict="GAME_EXITED", reason="war3.exe ended before SELFTEST DONE", exit_code=EXIT_NO_RESULT)
        elif not war3 and elapsed > args.start_timeout:
            outcome = dict(state, verdict="NO_GAME", reason=f"war3.exe did not start within {args.start_timeout} s", exit_code=EXIT_NO_RESULT)
        elif time.time() >= deadline:
            outcome = dict(state, verdict="TIMEOUT", reason=f"no SELFTEST DONE within {args.timeout} s", exit_code=EXIT_TIMEOUT)
        elif not state["done"] and time.time() - last_change > args.stall:
            outcome = dict(state, verdict="STALLED", reason=f"no new result for {args.stall} s: paused game or hang", exit_code=EXIT_TIMEOUT)
    return outcome


def finish_run(slot, evidence, result, xvfb, personal_before, foreign_start, log, gate):
    report = cleanup_slot(slot, result.get("verdict", "end of run"))
    if xvfb is not None and xvfb.poll() is None:
        stop_xvfb(xvfb)
        report["xvfb_stopped_by_handle"] = True
    report["after_final"] = own_processes(slot)
    write_json(evidence / "cleanup.json", report)
    result["cleanup_clean"] = not report["after_final"]
    if no_symlink_chain(slot.prefix):      # refused earlier: never read through it
        result["ended"], result["evidence"] = now(), str(evidence)
        write_json(evidence / "result.json", result)
        log(f"RESULT {result['verdict']} exit {result['exit_code']}  {result.get('reason', '')}")
        return

    # Everything below is read after the game is gone, so a late crash or a half-written file cannot pass.
    results_mtime = None
    lines = []
    if slot.results.exists():
        try:
            slot.assert_own(slot.results)
            results_mtime = os.stat(slot.results).st_mtime
            lines = read_results(slot.results)
            shutil.copy2(slot.results, evidence / "cd_test.txt")
            result["results_sha256"] = sha256(slot.results)
        except (OSError, Refused) as e:
            result["results_copy_error"] = str(e)
    result.update(evaluate_results(lines))
    result["results_fresh"] = results_mtime is not None and gate["game_started"] is not None and results_mtime >= gate["game_started"]
    new_crash = crash_changes(gate["crash_before"], crash_fingerprint(slot)) if gate["crash_before"] is not None else set()
    result["crash_evidence_new"] = sorted(new_crash)
    for item in sorted(new_crash):
        if os.path.isfile(item):
            target = evidence / "crash" / os.path.relpath(item, slot.dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    prior = (result.get("verdict"), result.get("reason", ""), result.get("exit_code", EXIT_INTERRUPTED))
    result["verdict"], result["reason"], result["exit_code"] = final_gate(prior, lines, results_mtime, gate["game_started"], new_crash)
    if not result["cleanup_clean"] and result["exit_code"] == EXIT_OK:
        result.update(verdict="CLEANUP_FAILED", reason=f"left behind: {report['after_final']}", exit_code=EXIT_ISOLATION)
    if slot.prefix.is_dir() and (slot.prefix / "dosdevices").is_dir():
        audit = prefix_audit(slot)
        write_json(evidence / "prefix-audit-after.json", audit)
        if audit["bad"] and result["exit_code"] == EXIT_OK:
            result.update(verdict="ISOLATION_VIOLATION", reason=f"prefix audit after the run: {audit['bad']}", exit_code=EXIT_ISOLATION)

    foreign_end = foreign_clients()
    survived = [dict(c, survived=same_process(c)) for c in foreign_start]
    windows_after = host_windows()
    write_json(evidence / "foreign-after.json", {"clients": foreign_end, "start_clients_survived": survived, "host_windows": windows_after, "at": now()})
    result["foreign_clients"] = survived
    if windows_after.get("available"):
        result["host_windows_wine"] = windows_after["wine"]
    if personal_before is not None:
        diff = snapshot_diff(personal_before, personal_snapshot())
        client_active = bool(foreign_start or foreign_end or (evidence / "foreign.jsonl").exists())
        write_json(evidence / "personal-diff.json", {"zero": not diff, "client_active_during_run": client_active, "diff": diff})
        result["personal_diff"] = {"zero": not diff, "entries": len(diff), "client_active_during_run": client_active}
        if diff and not client_active and result["exit_code"] == EXIT_OK:
            result.update(verdict="ISOLATION_VIOLATION", reason=f"personal data changed: {list(diff)[:5]}", exit_code=EXIT_ISOLATION)
    result["ended"] = now()
    result["evidence"] = str(evidence)
    write_json(evidence / "result.json", result)
    log(f"RESULT {result['verdict']} exit {result['exit_code']}  PASS {result.get('pass', 0)} FAIL {result.get('fail', 0)}  {result.get('reason', '')}")
    log(f"evidence: {evidence}")


# ---------------------------------------------------------------------------------------------------------------------
# Commands.

def cmd_status(_args):
    validate_root()
    slots_dir = ROOT / "slots"
    for name in sorted(os.listdir(slots_dir)) if slots_dir.is_dir() else []:
        slot = Slot(name)
        procs = own_processes(slot)
        print(f"slot {name}: {len(procs)} processes  {[(p['pid'], p['comm']) for p in procs]}  state {read_state(slot)}")
    print(f"other clients: {foreign_clients()}")
    return 0


def cmd_cleanup(args):
    validate_root()
    names = [args.slot] if args.slot else (sorted(os.listdir(ROOT / "slots")) if (ROOT / "slots").is_dir() else [])
    code = 0
    for name in names:
        slot = Slot(name)
        fd = os.open(slot.dir / "lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            if not args.force:
                print(f"slot {name}: a run owns it, not touching it (--force to stop that run)")
                code = code or 1
                os.close(fd)
                continue
        report = cleanup_slot(slot, "manual cleanup")
        os.close(fd)
        print(json.dumps({k: report[k] for k in ("slot", "clean", "signalled")}, default=str))
        code = code or (0 if report["clean"] else 1)
    return code


class Proof:
    """A list of named checks that ends in summary.json + summary.md. One failed check = exit 1."""

    def __init__(self, name):
        validate_root()
        self.id = f"{name}-{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
        self.dir = ROOT / "evidence" / self.id
        self.dir.mkdir(parents=True)
        self.checks = []
        print(f"evidence: {self.dir}", flush=True)

    def say(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)
        with open(self.dir / "log.txt", "a", encoding="utf-8") as f:
            f.write(f"{now()} {message}\n")

    def check(self, name, ok, detail=""):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        self.say(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}".rstrip())
        return bool(ok)

    def finish(self, limit, extra=None):
        failed = [c for c in self.checks if not c["ok"]]
        write_json(self.dir / "summary.json", {"id": self.id, "ended": now(), "passed": len(self.checks) - len(failed), "failed": len(failed), "limit": limit, "checks": self.checks, **(extra or {})})
        lines = [f"# {self.id}", "", f"{len(self.checks) - len(failed)} passed, {len(failed)} failed.", "", f"**Limit:** {limit}", ""]
        lines += [f"- {'PASS' if c['ok'] else 'FAIL'} {c['check']} {c['detail']}".rstrip() for c in self.checks]
        (self.dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.say(f"RESULT {len(self.checks) - len(failed)} passed, {len(failed)} failed: {self.dir}")
        return 1 if failed else 0


class Client:
    """A hidden run started as its own process, seen only through its evidence files."""

    def __init__(self, proof, label, slot, *options, env=None):
        self.label, self.slot_name = label, slot
        self.run_id = f"{proof.id}-{label}"
        self.dir = ROOT / "evidence" / self.run_id
        self.out = open(proof.dir / f"{label}.out", "wb")
        self.proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run", "--slot", slot, "--run-id", self.run_id, *options],
                                     stdout=self.out, stderr=self.out, start_new_session=True, env=env)

    def status(self):
        try:
            return json.loads((self.dir / "status.json").read_text())
        except (OSError, ValueError):
            return {}

    def result(self):
        try:
            return json.loads((self.dir / "result.json").read_text())
        except (OSError, ValueError):
            return {}

    def wait_status(self, test, seconds):
        end = time.time() + seconds
        while time.time() < end:
            current = self.status()
            if current and test(current):
                return current
            if self.proc.poll() is not None:
                return None
            pause(1)
        return None

    def wait_exit(self, seconds):
        try:
            return self.proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return None

    def identity(self):
        war3 = self.status().get("war3") or {}
        return {"pid": war3.get("pid"), "starttime": war3.get("starttime")}


def checkpoint(proof, name, clients):
    rows = {}
    for client in clients:
        current = client.status()
        identity = client.identity()
        rows[client.label] = {"war3": identity, "alive": bool(identity["pid"]) and same_process(identity), "pass": current.get("pass"), "cpu_ticks": current.get("cpu_ticks"),
                              "display": current.get("display"), "wineserver": current.get("wineserver"), "prefix": str(Slot(client.slot_name).prefix)}
    append_jsonl(proof.dir / "checkpoints.jsonl", {"at": now(), "name": name, "clients": rows, "others": foreign_clients(), "host_windows": host_windows()})
    return rows


def moved_on(client, seconds=90):
    """Same process, and a new result line from now on. A client that already finished sits on the victory dialog,
    which pauses the game: there only a live process with CPU activity can be shown, not a running game clock."""
    identity = client.identity()
    before = client.status()
    end = time.time() + seconds
    while time.time() < end:
        current = client.status()
        if not same_process(identity):
            return False, "process gone"
        if (current.get("pass") or 0) > (before.get("pass") or 0):
            return True, f"PASS {before.get('pass')} -> {current.get('pass')}"
        if current.get("done") and (current.get("cpu_ticks") or 0) > (before.get("cpu_ticks") or 0) + 100:
            return True, f"test already over: process alive, CPU ticks {before.get('cpu_ticks')} -> {current.get('cpu_ticks')} (no claim about the game clock)"
        pause(1)
    return False, f"no progress in {seconds} s"


def in_game(status):
    return (status.get("pass") or 0) >= 1 and bool(status.get("war3"))


def slot_quiet(name):
    return not own_processes(Slot(name))


def stop_clients(clients):
    for client in clients:
        if client.proc.poll() is None:
            client.proc.send_signal(signal.SIGTERM)
    for client in clients:
        client.wait_exit(60)


LIMIT_TWO = ("Two hidden clients on separate Xvfb displays and prefixes: a simulated concurrency, not a session played by Jiri. It does not exercise his "
             "real display, GPU, audio or launcher, or how the game feels beside a test. A client that has finished is held on the victory dialog, which pauses "
             "the game: there it shows a live process with CPU activity, not a running game clock. Game progress is proven by the PASS lines and the full runs.")
LIMIT_REAL = "A real client was present and observed read-only. Its identity and survival are proven; how the game felt to the player is not."


def concurrency_branch(others):
    """Only a real game justifies the read-only branch: a lone wineserver proves no second game."""
    real_games = [c for c in others if c["comm"].lower().startswith("war3")]
    return ("real-client" if real_games else "two-hidden"), real_games


def concurrency_with_real_client(proof, clients, real_games, remaining):
    proof.say(f"a real game runs: {real_games}. One hidden run beside it, nothing else.")
    a = Client(proof, "a", "a", "--timeout", str(int(remaining())))
    clients.append(a)
    during = a.wait_status(in_game, min(600, remaining()))
    proof.check("hidden client reached the game", during, f"{during}")
    checkpoint(proof, "during", [a])
    proof.check("real games alive during the run", all(same_process(c) for c in real_games))
    code = a.wait_exit(remaining())
    proof.check("hidden run exit 0", code == 0, f"exit {code} {a.result().get('verdict')}")
    checkpoint(proof, "after cleanup", [a])


def concurrency_two_hidden(proof, clients, hold, remaining):
    a = Client(proof, "a", "a", "--hold-file", str(hold), "--timeout", str(int(remaining())))
    clients.append(a)
    before = a.wait_status(in_game, 300)
    if not proof.check("A in game before B starts", before, f"PASS {(before or {}).get('pass')}"):
        return
    identity_a = a.identity()
    checkpoint(proof, "A alone", [a])
    map_copy = str(a.dir / TEST_MAP)

    def a_unharmed(after_what):
        proof.check(f"A same process after {after_what}", a.identity() == identity_a and same_process(identity_a), f"{identity_a}")
        moved, detail = moved_on(a)
        proof.check(f"A went on after {after_what}", moved, detail)

    # 1. B ends by timeout
    b1 = Client(proof, "b1-timeout", "b", "--timeout", "30", "--map", map_copy)
    clients.append(b1)
    code = b1.wait_exit(120)
    proof.check("B timeout: exit 3", code == EXIT_TIMEOUT, f"exit {code} {b1.result().get('verdict')}")
    proof.check("B timeout: slot b empty", slot_quiet("b") and b1.result().get("cleanup_clean"))
    checkpoint(proof, "after B timeout", [a, b1])
    a_unharmed("B start and timeout")

    # 2. both in game, different identities, then B is interrupted
    b2 = Client(proof, "b2-interrupt", "b", "--map", map_copy, "--timeout", "600")
    clients.append(b2)
    in_b = b2.wait_status(in_game, 300)
    proof.check("B in game while A runs", in_b, f"PASS {(in_b or {}).get('pass')}")
    rows = checkpoint(proof, "both in game", [a, b2])
    status_a, status_b = a.status(), b2.status()
    server_a, server_b = status_a.get("wineserver") or {}, status_b.get("wineserver") or {}
    proof.check("different war3 processes", a.identity()["pid"] != b2.identity()["pid"], f"{a.identity()} {b2.identity()}")
    proof.check("different wineservers and server dirs", server_a and server_b and server_a["pid"] != server_b["pid"] and server_a["server_dir"] != server_b["server_dir"], f"{server_a} {server_b}")
    proof.check("different private displays", status_a.get("display") != status_b.get("display"), f":{status_a.get('display')} :{status_b.get('display')}")
    proof.check("both alive at the same moment", all(r["alive"] for r in rows.values()), f"{rows}")
    b2.proc.send_signal(signal.SIGTERM)
    code = b2.wait_exit(90)
    proof.check("B interrupted: exit 130", code == EXIT_INTERRUPTED, f"exit {code} {b2.result().get('verdict')}")
    proof.check("B interrupted: slot b empty", slot_quiet("b") and b2.result().get("cleanup_clean"))
    checkpoint(proof, "after B interrupt", [a, b2])
    a_unharmed("B start and interrupt")

    # 3. the B runner dies with kill -9: the watchdog cleans its slot and nothing else
    b3 = Client(proof, "b3-kill9", "b", "--map", map_copy, "--timeout", "600")
    clients.append(b3)
    in_b = b3.wait_status(lambda st: bool(st.get("war3")), 120)
    proof.check("B started again without manual cleanup", in_b, f"{(in_b or {}).get('war3')}")
    b3.proc.send_signal(signal.SIGKILL)
    b3.wait_exit(10)
    end = time.time() + 60
    while time.time() < end and not ((b3.dir / "cleanup-watchdog.json").exists() and slot_quiet("b")):
        pause(1)
    proof.check("B runner killed: watchdog emptied slot b", slot_quiet("b") and (b3.dir / "cleanup-watchdog.json").exists())
    checkpoint(proof, "after B kill -9", [a, b3])
    a_unharmed("B kill -9 and watchdog cleanup")

    # 4. B runs normally; A ends and cleans up while B plays; then B finishes
    b4 = Client(proof, "b4-normal", "b", "--map", map_copy, "--timeout", str(int(remaining())))
    clients.append(b4)
    in_b = b4.wait_status(in_game, 300)
    proof.check("B in game again", in_b, f"PASS {(in_b or {}).get('pass')}")
    a_done = a.wait_status(lambda st: st.get("done"), remaining())
    proof.check("A reached SELFTEST DONE beside B", a_done)
    identity_b = b4.identity()
    checkpoint(proof, "before A cleanup", [a, b4])
    hold.write_text("release\n")
    code = a.wait_exit(120)
    result_a = a.result()
    proof.check("A exit 0 with clean results", code == 0 and result_a.get("verdict") == "PASS", f"exit {code} {result_a.get('verdict')} PASS {result_a.get('pass')} FAIL {result_a.get('fail')}")
    proof.check("A cleanup left slot a empty", slot_quiet("a") and result_a.get("cleanup_clean"))
    proof.check("B same process after A cleanup", b4.identity() == identity_b and same_process(identity_b), f"{identity_b}")
    checkpoint(proof, "after A cleanup", [a, b4])
    if not b4.status().get("done"):
        moved, detail = moved_on(b4, 180)
        proof.check("B went on after A cleanup", moved, detail)
    code = b4.wait_exit(remaining())
    result_b = b4.result()
    proof.check("B exit 0 with clean results", code == 0 and result_b.get("verdict") == "PASS", f"exit {code} {result_b.get('verdict')} PASS {result_b.get('pass')} FAIL {result_b.get('fail')}")
    proof.check("B cleanup left slot b empty", slot_quiet("b") and result_b.get("cleanup_clean"))


def cmd_concurrency(args):
    """If the owner's client runs: one hidden run beside it, read-only towards it. Otherwise two hidden clients, with
    the timeout, interrupt and kill -9 ends of one while the other plays, then each surviving the other's normal end."""
    proof = Proof("concurrency")
    personal_before = personal_snapshot()
    others = foreign_clients()
    branch, real_games = concurrency_branch(others)
    proof.say(f"branch {branch}; real games {real_games}; all other Wine processes {others}")
    write_json(proof.dir / "others-before.json", {"branch": branch, "real_games": real_games, "clients": others, "host_windows": host_windows()})
    clients = []
    deadline = time.time() + args.timeout

    def remaining():
        return max(30, deadline - time.time())

    def on_signal(signum, _frame):
        raise Interrupted(signal.Signals(signum).name)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, on_signal)
    try:
        if real_games:
            concurrency_with_real_client(proof, clients, real_games, remaining)
        else:
            concurrency_two_hidden(proof, clients, proof.dir / "release-a", remaining)
    except Interrupted as e:
        proof.check("concurrency proof finished", False, f"interrupted by {e}")
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        stop_clients(clients)

    # What holds for every ending.
    proof.check("no client process left in any slot", slot_quiet("a") and slot_quiet("b"))
    locks = [f"/tmp/.X{c.status().get('display')}-lock" for c in clients if c.status().get("display")]
    proof.check("no private display left", not any(os.path.exists(lock) for lock in locks), f"{sorted(set(locks))}")
    others_end = foreign_clients()
    diff = snapshot_diff(personal_before, personal_snapshot())
    write_json(proof.dir / "personal-diff.json", {"zero": not diff, "client_active": bool(others or others_end), "diff": diff})
    if real_games:
        proof.check("real games survived start and every cleanup", all(same_process(c) for c in real_games), f"{real_games}")
    if others or others_end:
        # A lone wineserver may end by itself, so it is observed and reported, not judged.
        proof.say(f"other Wine processes: at start {[dict(c, alive=same_process(c)) for c in others]}, now {others_end}")
        proof.say(f"personal data diff not judged, other Wine processes were active: {sorted(diff)[:8]}")
    else:
        proof.check("personal data: zero diff", not diff, f"{sorted(diff)[:8]}")
    windows = host_windows()
    write_json(proof.dir / "others-after.json", {"clients": others_end, "host_windows": windows})
    if not others and not others_end:
        proof.check("no window of ours on the owner's display", windows.get("available") and not windows["wine"], f"{windows}")
    return proof.finish(LIMIT_REAL if real_games else LIMIT_TWO, {"branch": branch, "real_games": real_games, "clients": [c.run_id for c in clients], "others": others})


def cmd_verify_branches(_args):
    """Refusals, the final gate, and the ways a run can go wrong, each with a real game where a game is involved."""
    proof = Proof("branches")
    limit = "Error paths of the runner on this machine. A real crash inside the game is covered by the gate test, not provoked."
    tool = [sys.executable, str(Path(__file__).resolve())]
    sandbox = proof.dir / "sandbox"
    sandbox.mkdir()

    # --- refusals: nothing may start
    def refused(name, env_root, *cmd):
        reg_before = sha256(HOME / ".wine" / "user.reg") if (HOME / ".wine" / "user.reg").exists() else None
        done = subprocess.run(tool + list(cmd), env=dict(os.environ, CD_TEST_ROOT=str(env_root)), capture_output=True, text=True, check=False)
        same = reg_before == (sha256(HOME / ".wine" / "user.reg") if reg_before else None)
        proof.check(f"refused: {name}", done.returncode == EXIT_REFUSED and same, f"exit {done.returncode} {(done.stderr or done.stdout).strip().splitlines()[-1:]}")

    refused("the personal ~/.wine as root", HOME / ".wine", "run", "--slot", "a")
    refused("a root inside the real game", REAL_GAME / "test-env", "run", "--slot", "a")
    real_root = sandbox / "real"
    real_root.mkdir()
    (sandbox / "link").symlink_to(real_root)
    refused("a symlinked root", sandbox / "link", "run", "--slot", "a")
    swapped = sandbox / "swapped"
    (swapped / "slots" / "a").mkdir(parents=True)
    (swapped / "slots" / "a" / "prefix").symlink_to(HOME / ".wine")
    refused("a slot prefix that is a symlink to ~/.wine", swapped, "run", "--slot", "a", "--map", "/dev/null")
    refused("a bad slot name", sandbox / "real", "run", "--slot", "../x")

    # --- the gate, without a game
    fresh = 2000.0
    done_lines = ["PASS x", "SELFTEST DONE"]
    ok = ("PASS", "", EXIT_OK)
    cases = [("clean", (ok, done_lines, fresh, 1000.0, set()), EXIT_OK),
             ("DONE plus a new crash", (ok, done_lines, fresh, 1000.0, {"crash"}), EXIT_CRASH),
             ("stale results", (ok, done_lines, 500.0, 1000.0, set()), EXIT_NO_RESULT),
             ("no results file", (ok, [], None, 1000.0, set()), EXIT_NO_RESULT),
             ("no DONE line", (ok, ["PASS x"], fresh, 1000.0, set()), EXIT_NO_RESULT),
             ("FAIL line", (ok, ["PASS x", "FAIL y", "SELFTEST DONE"], fresh, 1000.0, set()), EXIT_FAILED_CHECKS),
             ("DONE without any PASS", (ok, ["SELFTEST DONE"], fresh, 1000.0, set()), EXIT_NO_RESULT),
             ("timeout stays timeout", (("TIMEOUT", "t", EXIT_TIMEOUT), done_lines, fresh, 1000.0, set()), EXIT_TIMEOUT),
             ("timeout plus a crash", (("TIMEOUT", "t", EXIT_TIMEOUT), [], None, 1000.0, {"crash"}), EXIT_CRASH)]
    for name, gate_args, wanted in cases:
        verdict = final_gate(*gate_args)
        proof.check(f"gate: {name}", verdict[2] == wanted, f"{verdict[0]} exit {verdict[2]}")

    # --- only a real game justifies the read-only concurrency branch
    wineserver, game = {"comm": "wineserver"}, {"comm": "war3.exe"}
    for name, others, wanted in (("nothing else", [], "two-hidden"), ("a lone wineserver", [wineserver], "two-hidden"),
                                 ("a game", [game], "real-client"), ("a wineserver and a game", [wineserver, game], "real-client")):
        proof.check(f"concurrency branch: {name}", concurrency_branch(others)[0] == wanted, concurrency_branch(others)[0])

    # --- a hostile inherited environment and a map without results: must time out, in its own prefix and display
    garbage = sandbox / "garbage.w3x"
    garbage.write_bytes(b"not a map")
    hostile = dict(os.environ, WINEPREFIX=str(HOME / ".wine"), WINESERVER="/bin/false", WINELOADER="/bin/false", WINEPATH="C:\\evil", WINEDLLPATH="/nonexistent", WINEDLLOVERRIDES="d3d9=b;d3d8=b",
                   WINEDEBUG="+all", WINEARCH="win32", WAYLAND_DISPLAY="wayland-0", PULSE_SERVER="tcp:127.0.0.1", XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000"))
    t = Client(proof, "timeout-hostile-env", "a", "--map", str(garbage), "--timeout", "40", "--start-timeout", "30", env=hostile)
    code = t.wait_exit(180)
    result = t.result()
    proof.check("no results: run fails", code in (EXIT_TIMEOUT, EXIT_NO_RESULT), f"exit {code} {result.get('verdict')} {result.get('reason')}")
    proof.check("no results: slot empty afterwards", slot_quiet("a") and result.get("cleanup_clean"))
    try:
        env_lines = json.loads((t.dir / "war3-env.json").read_text())
    except (OSError, ValueError):
        env_lines = []
    wanted = {f"WINEPREFIX={Slot('a').prefix}", "WINEDEBUG=-all", "WINEARCH=win64", "WINEDLLOVERRIDES=winemenubuilder.exe=d;mscoree=d;mshtml=d;d3d8=n;d3d9=n"}
    proof.check("hostile env did not reach the game", env_lines and wanted <= set(env_lines) and not any(line.startswith(("WINESERVER=", "WINEPATH=", "WINEDLLPATH=", "WINELOADER=/bin/false", "WAYLAND_DISPLAY=", "PULSE_SERVER=tcp")) for line in env_lines), f"{env_lines}")
    proof.check("hostile env: private display only", any(re.fullmatch(r"DISPLAY=:[1-9]\d*", line) and line != f"DISPLAY={os.environ.get('DISPLAY')}" for line in env_lines))

    # --- the game dies during the test
    k = Client(proof, "game-killed", "a", "--timeout", "300")
    up = k.wait_status(lambda st: bool(st.get("war3")), 120)
    proof.check("game-killed: game started", up)
    if up:
        war3 = up["war3"]
        proof.check("game-killed: verified signal hit our own game", signal_verified(Slot("a"), war3["pid"], war3["starttime"], signal.SIGKILL), f"{war3}")
    code = k.wait_exit(120)
    result = k.result()
    proof.check("game-killed: exit 4, no PASS", code == EXIT_NO_RESULT, f"exit {code} {result.get('verdict')} {result.get('reason')}")
    proof.check("game-killed: slot empty afterwards", slot_quiet("a") and result.get("cleanup_clean"))

    # --- crash evidence is a fingerprint: an entry in an old log counts, an untouched old file does not
    errors = Slot("a").game / "Errors"
    errors.mkdir(parents=True, exist_ok=True)
    old_log = errors / "verify-old-log.txt"
    old_log.write_text("an old entry\n")
    fake = types.SimpleNamespace(prefix=Slot("a").prefix, game=Slot("a").game)
    base = crash_fingerprint(fake)
    proof.check("crash fingerprint: unchanged = nothing new", not crash_changes(base, crash_fingerprint(fake)))
    with open(old_log, "a", encoding="utf-8") as f:
        f.write("a new entry\n")
    proof.check("crash fingerprint: append to an old log", str(old_log) in crash_changes(base, crash_fingerprint(fake)))
    base = crash_fingerprint(fake)
    stamp = os.stat(old_log)
    old_log.write_bytes(old_log.read_bytes().replace(b"new", b"NEW"))
    os.utime(old_log, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    proof.check("crash fingerprint: same size and mtime, other bytes", str(old_log) in crash_changes(base, crash_fingerprint(fake)))
    c = Client(proof, "crash-in-old-log", "a", "--map", str(garbage), "--timeout", "120")
    up = c.wait_status(lambda st: bool(st.get("war3")), 60)
    proof.check("crash in an old log: game started", up)
    with open(old_log, "a", encoding="utf-8") as f:
        f.write("written during the run\n")
    code = c.wait_exit(60)
    proof.check("crash in an old log: exit 5", code == EXIT_CRASH, f"exit {code} {c.result().get('verdict')} {c.result().get('reason')}")
    proof.check("crash in an old log: slot empty afterwards", slot_quiet("a") and c.result().get("cleanup_clean"))

    # --- a clean test that gets a crash entry only after SELFTEST DONE must not pass
    hold = proof.dir / "release-crash"
    d = Client(proof, "crash-after-done", "a", "--hold-file", str(hold), "--timeout", "1200")
    done = d.wait_status(lambda st: st.get("done"), 1200)
    proof.check("crash after DONE: the test reached SELFTEST DONE", done, f"PASS {(done or {}).get('pass')}")
    with open(old_log, "a", encoding="utf-8") as f:
        f.write("written after SELFTEST DONE\n")
    hold.write_text("release\n")
    code = d.wait_exit(120)
    proof.check("crash after DONE: exit 5, not PASS", code == EXIT_CRASH, f"exit {code} {d.result().get('verdict')} {d.result().get('reason')}")
    old_log.unlink()

    # --- another client is up (a stand-in with the game's process name): recorded, never touched, on timeout too
    # A script, because /bin/sleep here is a multi-call binary that dies under another name.
    stand_in = sandbox / "war3.exe"
    stand_in.write_text("#!/bin/sh\nwhile :; do sleep 5; done\n")
    stand_in.chmod(0o755)
    other = subprocess.Popen([str(stand_in)], start_new_session=True)
    try:
        pause(0.5)
        identity = {"pid": other.pid, "starttime": proc_info(other.pid)["starttime"]}
        proof.check("other client: stand-in is running under the game's name", other.poll() is None and proc_info(other.pid)["comm"] == "war3.exe" and proc_info(other.pid)["state"] != "Z", f"{proc_info(other.pid)}")
        f = Client(proof, "beside-other-client", "a", "--map", str(garbage), "--timeout", "30", "--start-timeout", "25")
        code = f.wait_exit(180)
        result = f.result()
        seen = [c for c in result.get("foreign_clients", []) if c["pid"] == other.pid]
        proof.check("other client: run ended by timeout", code == EXIT_TIMEOUT, f"exit {code} {result.get('verdict')}")
        proof.check("other client: seen by the run", seen, f"{seen}")
        proof.check("other client: survived start, timeout and cleanup", same_process(identity) and seen and seen[0]["survived"], f"{identity}")
    finally:
        os.killpg(other.pid, signal.SIGTERM)
        other.wait()

    # --- nothing left, and a clean run still works straight after all of that
    proof.check("slots empty", slot_quiet("a") and slot_quiet("b"))
    n = Client(proof, "clean-after-failures", "a", "--timeout", "1200")
    code = n.wait_exit(1300)
    result = n.result()
    proof.check("a clean run right after the failures: exit 0, no manual cleanup", code == 0 and result.get("verdict") == "PASS", f"exit {code} {result.get('verdict')} PASS {result.get('pass')} FAIL {result.get('fail')}")
    proof.check("slots empty at the end", slot_quiet("a") and slot_quiet("b"))
    return proof.finish(limit)


def add_run_options(parser):
    parser.add_argument("--slot", default="auto", help="a, b, or auto = the first free one")
    parser.add_argument("--map", help="a built TEST map (default: build it now with --test --no-install)")
    parser.add_argument("--timeout", type=int, default=1200, help="seconds for the whole run")
    parser.add_argument("--stall", type=int, default=300, help="seconds without a new result line = paused or hung")
    parser.add_argument("--start-timeout", type=int, default=120)
    parser.add_argument("--shot-every", type=int, default=30)
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument("--run-id")
    parser.add_argument("--hold-file", help="after SELFTEST DONE keep the game running until this file exists")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    add_run_options(sub.add_parser("run"))
    sub.add_parser("status")
    conc = sub.add_parser("concurrency")
    conc.add_argument("--timeout", type=int, default=1500)
    sub.add_parser("verify-branches")
    cleanup_parser = sub.add_parser("cleanup")
    cleanup_parser.add_argument("--slot")
    cleanup_parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        return {"run": run_once, "status": cmd_status, "cleanup": cmd_cleanup, "concurrency": cmd_concurrency, "verify-branches": cmd_verify_branches}[args.command](args)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
