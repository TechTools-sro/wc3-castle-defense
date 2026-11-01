#!/bin/bash
# Automated in-game test: launches a map with -loadfile (skips the lobby), screenshots the window every 6 s,
# then kills ONLY its own war3 instance.
#
#   tools/run_test.sh 'Maps\Test\TechToolsCastleDefence_TEST.w3x' /tmp/out 40
#
# Copy the map into <game>/Maps/Test/ first (python3 build.py --test, then cp dist/*_TEST.w3x).
# Refuses to run while WarCraft III is already open: a second launch silently attaches to the running
# instance, and the owner's own game must never be killed (it shows as "z:\...\war3.exe").
# Crash check: count the folders in ~/.wine/drive_c/users/$USER/AppData/Local/Temp/BlizzardError/ before/after.
GAME_DIR="${WC3_DIR:-/home/novakj/games/warcraft3}"
if ps -eo stat,args | grep -iE 'war3\.exe' | grep -v grep | grep -v '^Z' >/dev/null; then
  echo "ABORT: WarCraft III is already running - not touching it"; exit 3
fi
cd "$GAME_DIR" || exit 2
export DISPLAY="${DISPLAY:-:0}"
OUT="$2"; mkdir -p "$OUT"; rm -f "$OUT"/*.png
RESULTS="$GAME_DIR/CustomMapData/TestResults/cd_test.txt"; rm -f "$RESULTS"
# A Wine virtual desktop: WarCraft pauses a single-player game when its window loses focus (the clock froze at 0:11 for a
# whole run while the owner used the PC, 2026-11-01); inside the desktop it stays the active window.
# (explorer needs the absolute Windows path: with a bare war3.exe it opens an empty desktop and the game never starts)
WINEDEBUG=-all wine explorer /desktop=cdtest,1280x720 "Z:${GAME_DIR//\//\\}\\war3.exe" -window -loadfile "$1" > "$OUT/wine.log" 2>&1 &
END=$(( $(date +%s) + $3 ))
n=0
while [ "$(date +%s)" -lt $END ]; do
  grep -q 'SELFTEST DONE' "$RESULTS" 2>/dev/null && break   # the test is over: close the game now
  timeout 6 tail -f /dev/null
  n=$((n+6))
  wid=$(xdotool search --name 'Wine desktop' 2>/dev/null | head -1)
  [ -n "$wid" ] || wid=$(xdotool search --name '^Warcraft III$' 2>/dev/null | head -1)
  if [ -n "$wid" ]; then
    ffmpeg -loglevel error -y -f x11grab -window_id "$wid" -i :0 -frames:v 1 -vf scale=1280:-1 \
      "$OUT/s$(printf %03d $n).png" 2>>"$OUT/ffmpeg.log"
  fi
done
ps -eo pid,args | grep -E 'war3\.exe -window -loadfile|explorer\.exe /desktop=cdtest' | grep -v grep | awk '{print $1}' | xargs -r kill
echo done
